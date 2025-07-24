import os
import re
import sys
import time
import json
import logging
import shutil
from typing import Dict, Any, List, Set, Optional
from datetime import datetime
import google.generativeai as genai
import requests
from dotenv import load_dotenv
from json_repair import loads as json_repair_loads

# --- MODIFIED: Removed unused import 'singularize'
# from inflection import singularize

# --- ⚙️ 1. CONFIGURATION ---
load_dotenv()
FIGMA_API_KEY = os.getenv("FIGMA_API_KEY")
FIGMA_FILE_KEY = os.getenv("FIGMA_FILE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Settings ---
SCHEMAS_DIR = "schemaTypes1"
FIGMA_PAGE_NAME = "Page 1"
FIGMA_MAIN_FRAME_NAME = "Desktop"
GEMINI_MODEL_NAME = "gemini-2.5-flash"


# --- 🛠️ 2. HELPER & SETUP FUNCTIONS ---


def setup_logging():
    """
    Configures logging to output to both a clean console view and a detailed log file.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_path = os.path.join(log_dir, f"ai-schema-architect_{timestamp}.log")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    if logger.hasHandlers():
        logger.handlers.clear()
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler(log_file_path, "w", "utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    console_formatter = logging.Formatter("%(asctime)s - %(message)s")
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    logging.info(f"Logging configured. Detailed log saved to: {log_file_path}")


def to_pascal_case(text: str) -> str:
    return "".join(word.capitalize() for word in re.split(r"[\s_-]+", text))


def to_camel_case(text: str) -> str:
    pascal = to_pascal_case(text)
    return pascal[0].lower() + pascal[1:] if pascal else ""


def to_kebab_case(text: str) -> str:
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", text)
    return re.sub(r"([A-Z])", r"-\1", s1).lstrip("-").lower()


def extract_json_from_response(text: str) -> Optional[dict]:
    if not text:
        logging.warning("Received empty text from AI.")
        return None
    match = re.search(r"```(?:json)?\s*(\{[\s\S]+?\})\s*```", text, re.DOTALL)
    json_str = match.group(1).strip() if match else text.strip()
    try:
        return json_repair_loads(json_str)
    except Exception as e:
        logging.error(
            f"JSON repair failed: {e}\n--- AI Response Start ---\n{text}\n--- AI Response End ---"
        )
        return None


# --- 🖼️ 3. FIGMA DATA & SUMMARIZATION ---


def get_figma_document_data() -> Optional[dict]:
    if not FIGMA_API_KEY or not FIGMA_FILE_KEY:
        logging.error("Figma API token or file ID missing.")
        return None
    url = f"https://api.figma.com/v1/files/{FIGMA_FILE_KEY}"
    headers = {"X-Figma-Token": FIGMA_API_KEY}
    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        logging.info("✅ Fetched Figma file data successfully.")
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error fetching Figma file data: {e}")
        return None


def clean_node_for_ai(node: dict, depth=0, max_depth=7) -> Optional[dict]:
    if not node or depth > max_depth or not node.get("visible", True):
        return None
    cleaned = {"name": node.get("name", "Untitled"), "type": node.get("type")}
    if node.get("type") == "TEXT":
        cleaned["characters"] = node.get("characters")
    if any(f.get("type") == "IMAGE" for f in node.get("fills", [])):
        cleaned["isImagePlaceholder"] = True
    if "children" in node:
        children = [
            clean_node_for_ai(child, depth + 1, max_depth)
            for child in node.get("children", [])
        ]
        cleaned_children = [c for c in children if c]
        if cleaned_children:
            cleaned["children"] = cleaned_children
    return cleaned


def get_figma_page_sections() -> List[dict]:
    logging.info(
        f"📄 Fetching sections from Figma frame '{FIGMA_MAIN_FRAME_NAME}' on page '{FIGMA_PAGE_NAME}'..."
    )
    figma_data = get_figma_document_data()
    if not figma_data:
        return []
    try:
        document = figma_data["document"]
        target_page = next(
            (p for p in document["children"] if p.get("name") == FIGMA_PAGE_NAME), None
        )
        if not target_page:
            raise ValueError(f"Page '{FIGMA_PAGE_NAME}' not found.")
        main_frame = next(
            (
                f
                for f in target_page["children"]
                if f.get("type") == "FRAME" and f.get("name") == FIGMA_MAIN_FRAME_NAME
            ),
            None,
        )
        if not main_frame:
            raise ValueError(f"Main frame '{FIGMA_MAIN_FRAME_NAME}' not found.")
        sections = [
            {"name": n.get("name"), "node": n}
            for n in main_frame["children"]
            if n.get("type") in ["FRAME", "COMPONENT", "INSTANCE"] and n.get("name")
        ]
        if not sections:
            raise ValueError(f"No named sections found in '{FIGMA_MAIN_FRAME_NAME}'.")
        logging.info(f"✅ Found {len(sections)} top-level page sections.")
        return sections
    except (ValueError, KeyError, StopIteration) as e:
        logging.error(f"❌ Figma Error: {e}")
        return []


# --- 🤖 4. AI ARCHITECT ---


def phase_one_architect_plan(sections: List[dict], model) -> Optional[dict]:
    logging.info("🤖 PHASE 1: Creating architectural plan from Figma JSON...")
    sections_summary = [
        {"name": section["name"], "structure": clean_node_for_ai(section["node"])}
        for section in sections
    ]
    prompt = f"""
You are a top-tier Sanity.io Lead Architect. Analyze the lightweight JSON representation of a Figma design and create a high-level, scalable, and DRY schema plan.

**Architectural Rules:**
1.  **Documents vs. Objects:** `documents` are for queryable data collections (e.g., `post`, `page`, `siteSettings`). `objects` are for structural components used on pages (e.g., `heroSection`, `ctaButton`).
2.  **The Grid Rule:** When you see a "structure" with repeating children of the same name (e.g., a "Team" section with multiple "Team Member" children), define a `document` for the underlying data (e.g., `teamMember`) and an `object` for the page section (e.g., `teamSection`) that will hold an array of `references` to those documents.
3.  **Global Content Rule:** If you infer a 'Header' or 'Footer', plan a `siteSettings` document. Also plan for `headerSettings` and `footerSettings` objects (or documents if they are very complex), which will be referenced by `siteSettings`.
4.  **CRITICAL NAMING:** All names in your output MUST be in EXACT camelCase format (e.g., "metricsSection", "companyLogo", "heroSection").
5.  **Always include a `page` document.**

**Figma JSON Structure:**
{json.dumps(sections_summary, indent=2)}

**Your Output:**
Return ONLY a valid JSON object with `documents` and `objects` keys. The values for these keys must be arrays of camelCase schema names. Do not include a 'blocks' key.
"""
    logging.debug(
        f"\n--- PHASE 1: PROMPT SENT TO AI ---\n{prompt}\n---------------------------------"
    )
    try:
        response = model.generate_content(prompt)
        logging.debug(
            f"\n--- PHASE 1: RAW AI RESPONSE ---\n{response.text}\n------------------------------"
        )
        plan = extract_json_from_response(response.text)
        if not plan:
            raise ValueError("Phase 1 response did not contain valid JSON.")

        # Ensure all keys exist and normalize names to proper camelCase
        # --- MODIFIED: Simplified to just documents and objects
        for category in ["documents", "objects"]:
            plan.setdefault(category, [])
            plan[category] = sorted(
                list(set([to_camel_case(name) for name in plan[category]]))
            )
        if "page" not in plan["documents"]:
            plan["documents"].append("page")
            plan["documents"].sort()

        logging.info(f"✅ PHASE 1: Architectural plan received.")
        logging.debug(f"Plan details: {json.dumps(plan, indent=2)}")
        return plan
    except Exception as e:
        logging.error(f"❌ Gemini Error during Phase 1: {e}", exc_info=True)
        return None


def phase_two_generate_schema_code(
    schema_name: str, classification: str, plan: dict, sections: List[dict], model
) -> Optional[str]:
    logging.info(
        f"  🤖 PHASE 2: Generating TypeScript code for '{schema_name}' ({classification})..."
    )

    all_objects = plan.get("objects", [])
    all_documents = plan.get("documents", [])
    page_builder_objects = [
        obj
        for obj in all_objects
        if obj not in ["siteSettings", "headerSettings", "footerSettings"]
    ]

    relevant_section_json = next(
        (
            clean_node_for_ai(s["node"])
            for s in sections
            if to_camel_case(s["name"]) == schema_name
        ),
        None,
    )
    structure_info = (
        json.dumps(relevant_section_json, indent=2)
        if relevant_section_json
        else "No specific Figma structure found for this schema. Please generate a logical schema based on its name and classification."
    )

    special_instructions = ""
    if schema_name == "page":
        special_instructions = f"**SPECIAL INSTRUCTION FOR 'page':** This document MUST contain a `pageBuilder` field of type `array`. The `of` property for this array should be an array of objects, where each object has a `type` referencing one of the page sections from this list: {page_builder_objects}."
    elif schema_name == "siteSettings":
        special_instructions = "**SPECIAL INSTRUCTION FOR 'siteSettings':** This document must contain a `header` field of type `reference` to `headerSettings`, and a `footer` field of type `reference` to `footerSettings`."

    # --- MODIFIED: Enhanced prompt with specific fixes for the identified issues ---
    prompt = f"""
You are an expert Sanity.io schema generator. Your most important task is to create CONCISE and FOCUSED TypeScript schema code. 

### **CRITICAL: SCHEMA TYPE REQUIREMENT**
This schema MUST be of type: **'{classification}'**
Set the 'type' property in your defineType call to exactly: '{classification}'

### **CRITICAL: MINIMAL FIELD APPROACH**
- **Create ONLY essential content fields** - avoid over-engineering
- **Focus on actual content**, not visual styling or layout elements  
- **Maximum 3-5 fields per schema** unless absolutely necessary
- **Combine related fields** rather than creating separate ones for each visual element

### **Rule 1: Use `defineType` and `defineField`**
You MUST use the standard `defineType` and `defineField` functions imported from `sanity`.
`import {{defineType, defineField}} from 'sanity'`

### **Rule 2: Correct Validation Syntax (CRITICAL)**
For validation functions, **DO NOT** add an explicit type to the `Rule` parameter:
- **Correct:** `validation: (Rule) => Rule.required()`
- **INCORRECT:** `validation: (Rule: Rule) => Rule.required()`

### **Rule 3: Array Items - NO defineType Inside Arrays (CRITICAL)**
When defining array items in the `of` property, use plain object literals, NOT defineType:
- **Correct:** `of: [{{ name: 'item', type: 'object', fields: [...] }}]`
- **INCORRECT:** `of: [defineType({{ name: 'item', type: 'object', fields: [...] }})]`

### **Rule 3b: Array Type References - Always Use 'type:' Property (CRITICAL)**
When referencing other schemas in arrays, always include the 'type:' property:
- **Correct:** `of: [{{type: 'navigationitem'}}]`
- **INCORRECT:** `of: [{{'navigationitem'}}]`

### **Rule 3c: Multiple Items of Same Type in Arrays - Use Unique Names (CRITICAL)**
When an array contains multiple items of the same type, each must have a unique `name`:
- **Correct:** 
  ```
  of: [
    {{type: 'reference', name: 'primaryReference', to: [{{type: 'page'}}]}},
    {{type: 'reference', name: 'secondaryReference', to: [{{type: 'post'}}]}}
  ]
  ```

### **Rule 4: Internationalization Types - NO fields or 'of' Properties (CRITICAL)**
Custom i18n types do NOT support the `fields` or `of` properties:
- **Correct:** `{{name: 'description', type: 'internationalizedArrayText'}}`
- **INCORRECT:** `{{name: 'description', type: 'internationalizedArrayText', of: [...]}}`

**BLOCK CONTENT RULE:** 
- For rich text, quotes, or any content that would normally use `block` type, use `internationalizedArrayText`
- NEVER use `internationalizedArrayBlock` - it doesn't exist

### **Rule 5: Use Exact camelCase for Type References**
When referencing other schemas, use the exact camelCase names provided.
- **Available Documents for References:** {all_documents}
- **Available Objects for Embedding:** {all_objects}

### **Rule 6: Internationalization (i18n)**
Use i18n types for user-facing content:
- `internationalizedArrayString` - for short text fields
- `internationalizedArrayText` - for longer text content and rich text
- `internationalizedArrayImage` - for image fields  
- `internationalizedArrayFile` - for file uploads
- `internationalizedArrayUrl` - for URL fields
- `internationalizedArraySlug` - for slug fields

**REFERENCES DON'T NEED INTERNATIONALIZATION:**
- Use `reference` (NOT `internationalizedArrayReference`)

### **Rule 7: Previews (IMPORTANT)**
If a schema represents a visual component or content item, add a `preview` object:
- **For i18n string fields:** `title: 'title.0.value'`
- **For i18n image fields:** `media: 'image.0.value.asset'`
- **For regular fields:** `title: 'title'`, `media: 'image.asset'`
- **Add prepare function** to customize the preview display

**Example preview:**
```
preview: {{
  select: {{
    title: 'title.0.value',
    subtitle: 'description.0.value', 
    media: 'image.0.value.asset',
  }},
  prepare({{title, subtitle, media}}) {{
    return {{
      title: title || 'Untitled',
      subtitle: subtitle,
      media: media,
    }}
  }},
}}
```

### **Rule 8: Essential Fields Only**
**For ANY schema, include ONLY these types of fields:**
1. **Core Content**: Title, description, main text
2. **Media**: Primary image or icon (if essential)
3. **Actions**: CTA button or link (if needed)
4. **References**: Links to other content (if needed)

**DO NOT CREATE FIELDS FOR:**
- Visual styling (colors, spacing, layout)
- Multiple variations of the same content type
- Decorative elements
- Container or wrapper elements
- Every single visual element you see

### **Field Naming Convention:**
- Use simple, clear names: `title`, `description`, `image`, `button`
- Avoid verbose names like `primaryHeaderTitle`, `mainContentDescription`

---
**Your Task:**
Generate a MINIMAL, focused TypeScript schema for **`{schema_name}`** of type **'{classification}'** with ONLY essential content fields.

**Figma Structure to Analyze:**
```json
{structure_info}
```
{special_instructions}

**REMEMBER: The schema type MUST be '{classification}'. Focus on the CONTENT, not the visual design. Keep it simple and essential.**

Output ONLY the raw TypeScript code. Do not wrap it in markdown backticks or add any explanation.
"""
    logging.debug(
        f"\n--- PHASE 2: PROMPT SENT TO AI for '{schema_name}' ---\n{prompt}\n----------------------------------"
    )
    try:
        time.sleep(1.2)  # Rate limiting
        response = model.generate_content(prompt)
        logging.debug(
            f"\n--- PHASE 2: RAW AI RESPONSE for '{schema_name}' ---\n{response.text}\n------------------------------"
        )
        if response.text:
            logging.info(f" ✅ TypeScript code for '{schema_name}' generated.")
            return response.text
        raise ValueError("AI returned an empty response.")
    except Exception as e:
        logging.error(
            f"❌ Gemini Error during Phase 2 for '{schema_name}': {e}", exc_info=True
        )
        return None


# --- 📜 5. SANITY FILE GENERATOR & CORRECTION ---


# --- NEW: Comprehensive Correction Function ---
def correct_generated_code(
    code: str, all_valid_names: Set[str], expected_type: str = None
) -> str:
    """
    Applies a series of corrections to the AI-generated code to fix common, predictable errors.
    """
    original_code = code
    corrections_applied = []

    # Correction 0: Remove markdown formatting from generated code
    # Pattern: ```typescript or ```javascript or ``` at start/end of code
    if code.startswith("```") or code.endswith("```"):
        # Remove markdown code blocks
        code = re.sub(
            r"^```(?:typescript|javascript|ts|js)?\s*", "", code, flags=re.MULTILINE
        )
        code = re.sub(r"\s*```\s*$", "", code, flags=re.MULTILINE)
        corrections_applied.append("removed markdown formatting")

    # Also remove any stray markdown that might be in the middle
    if re.search(r";```\w*", code):
        code = re.sub(r";```\w*\s*", "", code)
        corrections_applied.append("removed stray markdown syntax")

    # Correction 0.5: Fix incorrect schema type (CRITICAL FIX for the main issue)
    if expected_type:
        # Find current type declaration
        type_pattern = r"type:\s*['\"]([^'\"]+)['\"]"
        type_match = re.search(type_pattern, code)
        if type_match:
            current_type = type_match.group(1)
            if current_type != expected_type:
                # Replace the type with the expected type
                code = re.sub(type_pattern, f"type: '{expected_type}'", code)
                corrections_applied.append(
                    f"schema type: '{current_type}' → '{expected_type}'"
                )

    # Correction 1: Fix incorrect validation function typing, e.g., (Rule: Rule) -> (Rule)
    validation_pattern = r"\(Rule:\s*[A-Za-z_][A-Za-z0-9_]*\)"
    code = re.sub(validation_pattern, r"(Rule)", code)
    if original_code != code:
        corrections_applied.append("validation function syntax (Rule: Rule) → (Rule)")

    # Correction 2: Fix defineType inside array 'of' properties
    # Pattern: of: [ defineType({ ... }) ] -> of: [ { ... } ]
    defineType_in_array_pattern = r"of:\s*\[\s*defineType\s*\(\s*\{"
    if re.search(defineType_in_array_pattern, code):
        code = re.sub(r"of:\s*\[\s*defineType\s*\(\s*\{", "of: [{", code)
        # Also fix the closing: }),] -> },]
        code = re.sub(r"\}\s*\)\s*,?\s*\]", "}]", code)
        corrections_applied.append("defineType inside arrays → plain objects")

    # Correction 3: Fix missing 'type:' property in array items
    # Pattern: of: [{'typeName'}] -> of: [{type: 'typeName'}]
    missing_type_pattern = r"of:\s*\[\s*\{\s*['\"]([^'\"]+)['\"]\s*\}\s*\]"
    if re.search(missing_type_pattern, code):
        code = re.sub(missing_type_pattern, r"of: [{type: '\1'}]", code)
        corrections_applied.append("added missing 'type:' property in array items")

    # Correction 4: Remove 'fields' property from internationalizedArray image types
    # Pattern: type: 'internationalizedArrayImage', ... fields: [...] -> type: 'internationalizedArrayImage', ...
    i18n_image_fields_pattern = r"(type:\s*['\"]internationalizedArray(Image|File)['\"][^}]*?),\s*fields:\s*\[[^\]]*?\]"
    if re.search(i18n_image_fields_pattern, code, re.DOTALL):
        code = re.sub(i18n_image_fields_pattern, r"\1", code, flags=re.DOTALL)
        corrections_applied.append("removed 'fields' from internationalizedArray type")

    # Correction 5: Remove 'of' property from internationalizedArray text/array types
    # Pattern: type: 'internationalizedArrayText', ... of: [...] -> type: 'internationalizedArrayText', ...
    i18n_array_of_pattern = r"(type:\s*['\"]internationalizedArray(?:Text|String|Url|Slug)['\"][^}]*?),\s*of:\s*\[[^\]]*?\]"
    if re.search(i18n_array_of_pattern, code, re.DOTALL):
        code = re.sub(i18n_array_of_pattern, r"\1", code, flags=re.DOTALL)
        corrections_applied.append("removed 'of' from internationalizedArray type")

    # Correction 6: Fix type name casing (existing logic)
    name_map = {name.lower(): name for name in all_valid_names}
    type_corrections = []

    def replace_type_reference(match):
        quote_char = match.group(1)
        type_name = match.group(2)
        # Skip correcting built-in types or i18n types
        built_in_types = {
            "string",
            "text",
            "image",
            "file",
            "url",
            "slug",
            "number",
            "boolean",
            "array",
            "object",
            "reference",
            "block",
            "date",
            "datetime",
        }
        if type_name in built_in_types or "internationalizedArray" in type_name:
            return match.group(0)

        type_name_lower = type_name.lower()
        if type_name_lower in name_map:
            correct_name = name_map[type_name_lower]
            if type_name != correct_name:
                type_corrections.append(f"'{type_name}' → '{correct_name}'")
                return f"{quote_char}{correct_name}{quote_char}"
        return match.group(0)

    type_pattern = r"type:\s*(['\"])([^'\"]+)\1"
    code = re.sub(type_pattern, replace_type_reference, code)

    if type_corrections:
        corrections_applied.append(
            f"type name casing: {', '.join(sorted(list(set(type_corrections))))}"
        )

    # Correction 5: Ensure imports are present (existing logic)
    if "defineType" not in code and "defineField" not in code:
        if "name:" in code and "title:" in code and "type:" in code:
            code = f"import {{defineType, defineField}} from 'sanity'\n\n{code}"
            corrections_applied.append("added missing defineType/defineField import")

    # Correction 6: Fix invalid internationalizedArray type names
    # Available types: String, Text, Image, File, Url, Slug
    invalid_i18n_types = {
        "internationalizedArrayOfPortableText": "internationalizedArrayText",
        "internationalizedArrayPortableText": "internationalizedArrayText",
        "internationalizedArrayRichText": "internationalizedArrayText",
        "internationalizedArrayBlock": "internationalizedArrayText",
        "internationalizedArrayContent": "internationalizedArrayText",
        "internationalizedArrayArray": "internationalizedArrayText",
        "internationalizedArrayReference": "reference",
        "internationalizedArrayCrossDatasetReference": "crossDatasetReference",
        "internationalizedArrayDocument": "reference",
    }
    for incorrect_name, correct_name in invalid_i18n_types.items():
        if incorrect_name in code:
            code = code.replace(incorrect_name, correct_name)
            corrections_applied.append(
                f"corrected invalid i18n type: {incorrect_name} → {correct_name}"
            )

    # Correction 7: Simplify verbose field names (anti-over-engineering)
    verbose_replacements = {
        r"name:\s*['\"]primaryTitle['\"]": "name: 'title'",
        r"name:\s*['\"]mainTitle['\"]": "name: 'title'",
        r"name:\s*['\"]headerTitle['\"]": "name: 'title'",
        r"name:\s*['\"]sectionTitle['\"]": "name: 'title'",
        r"name:\s*['\"]primaryDescription['\"]": "name: 'description'",
        r"name:\s*['\"]mainDescription['\"]": "name: 'description'",
        r"name:\s*['\"]sectionDescription['\"]": "name: 'description'",
        r"name:\s*['\"]primaryText['\"]": "name: 'text'",
        r"name:\s*['\"]mainText['\"]": "name: 'text'",
        r"name:\s*['\"]heroImage['\"]": "name: 'image'",
        r"name:\s*['\"]mainImage['\"]": "name: 'image'",
        r"name:\s*['\"]primaryImage['\"]": "name: 'image'",
        r"name:\s*['\"]featuredImage['\"]": "name: 'image'",
    }

    simplified_names = []
    for pattern, replacement in verbose_replacements.items():
        if re.search(pattern, code, re.IGNORECASE):
            code = re.sub(pattern, replacement, code, flags=re.IGNORECASE)
            simplified_names.append(pattern.split("'")[1])  # Extract the original name

    if simplified_names:
        corrections_applied.append(
            f"simplified verbose field names: {', '.join(simplified_names[:3])}{'...' if len(simplified_names) > 3 else ''}"
        )

    # Log all corrections applied
    if corrections_applied:
        logging.info(
            f"    🔧 Auto-corrections applied: {' | '.join(corrections_applied)}"
        )

    return code


def validate_generated_code(code: str, schema_name: str) -> List[str]:
    """
    Validates the generated code and returns a list of potential issues found.
    """
    issues = []

    # Check for markdown formatting that shouldn't be in TypeScript files
    if re.search(r"```\w*", code) or code.startswith("```") or code.endswith("```"):
        issues.append("❌ Found markdown formatting in TypeScript code")

    # Check for defineType inside arrays (should be caught by correction, but double-check)
    if re.search(r"of:\s*\[\s*defineType\s*\(", code):
        issues.append("❌ Found defineType inside array 'of' property")

    # Check for missing 'type:' property in array items
    if re.search(r"of:\s*\[\s*\{\s*['\"][^'\"]+['\"]\s*\}", code):
        issues.append("❌ Found missing 'type:' property in array items")

    # Check for fields property on i18n image types
    if re.search(
        r"type:\s*['\"]internationalizedArray(Image|File)['\"].*?fields:\s*\[",
        code,
        re.DOTALL,
    ):
        issues.append("❌ Found 'fields' property on internationalizedArray type")

    # Check for 'of' property on i18n text/array types
    if re.search(
        r"type:\s*['\"]internationalizedArray(?:Text|String|Url|Slug)['\"].*?of:\s*\[",
        code,
        re.DOTALL,
    ):
        issues.append("❌ Found 'of' property on internationalizedArray type")

    # Check for invalid internationalizedArray type names
    invalid_i18n_pattern = r"type:\s*['\"]internationalizedArray(?:OfPortableText|PortableText|RichText|Block|Content|Array|Of\w+)['\"]"
    if re.search(invalid_i18n_pattern, code):
        issues.append(
            "❌ Found invalid internationalizedArray type (only String, Text, Image, File, Url, Slug are available)"
        )

    # Check for invalid internationalizedArray reference types
    invalid_ref_pattern = r"type:\s*['\"]internationalizedArray(?:Reference|CrossDatasetReference|Document)['\"]"
    if re.search(invalid_ref_pattern, code):
        issues.append(
            "❌ Found invalid internationalizedArray reference type (use 'reference' instead - references don't need internationalization)"
        )

    # Check for explicit typing in validation functions
    if re.search(r"\(Rule:\s*[A-Za-z]", code):
        issues.append("❌ Found explicit typing in validation function parameter")

    # Check for missing imports
    if ("defineType" in code or "defineField" in code) and not re.search(
        r"import.*defineType.*from.*sanity", code
    ):
        issues.append("⚠️  Missing import for defineType/defineField")

    # Check for camelCase violations in type references
    type_references = re.findall(r"type:\s*['\"]([^'\"]+)['\"]", code)
    for type_ref in type_references:
        if type_ref[0].isupper() and "internationalizedArray" not in type_ref:
            # Skip built-in types
            built_in_types = {
                "String",
                "Text",
                "Image",
                "File",
                "Url",
                "Slug",
                "Number",
                "Boolean",
                "Array",
                "Object",
                "Reference",
                "Block",
                "Date",
                "Datetime",
            }
            if type_ref not in built_in_types:
                issues.append(f"⚠️  Type reference '{type_ref}' should be camelCase")

    # Check for schemas with too many fields (over-engineering detection)
    field_count = len(re.findall(r"defineField\s*\(", code))
    if field_count > 6:
        issues.append(
            f"⚠️  Schema has {field_count} fields - consider simplifying (recommended: 3-5 fields max)"
        )

    # Check for verbose field names that suggest over-engineering
    verbose_patterns = [
        r'name:\s*[\'"][a-z]*Title[A-Z][a-z]*[\'"]',  # e.g., "primaryTitle", "headerTitle"
        r'name:\s*[\'"][a-z]*Description[A-Z][a-z]*[\'"]',  # e.g., "mainDescription"
        r'name:\s*[\'"][a-z]*Text[A-Z][a-z]*[\'"]',  # e.g., "primaryText"
        r'name:\s*[\'"][a-z]*Image[A-Z][a-z]*[\'"]',  # e.g., "heroImage", "mainImage"
    ]

    for pattern in verbose_patterns:
        if re.search(pattern, code):
            issues.append(
                "⚠️  Found verbose field names - consider simpler naming (e.g., 'title', 'description', 'image')"
            )
            break  # Only show this warning once

    if issues:
        logging.warning(f"  ⚠️  Validation issues found in '{schema_name}':")
        for issue in issues:
            logging.warning(f"     {issue}")

    return issues


def validate_sanity_config():
    """
    Checks if sanity.config.ts configuration matches the chosen i18n approach.
    """
    config_file = "sanity.config.ts"
    if not os.path.exists(config_file):
        logging.warning("⚠️  sanity.config.ts not found in current directory")
        return

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config_content = f.read()

        # Check which approach is being used
        has_plugin_config = (
            "internationalizedArray" in config_content
            and "fieldTypes" in config_content
        )
        has_generated_import = (
            f"schemaTypes1" in config_content or f"{SCHEMAS_DIR}" in config_content
        )

        if has_plugin_config and has_generated_import:
            logging.warning(
                "⚠️  Both plugin configuration AND generated i18n files detected in sanity.config.ts"
            )
            logging.warning(
                "   Choose one approach: either use generated files OR plugin configuration, not both"
            )
        elif has_plugin_config:
            logging.info("✅ Using plugin-based internationalization configuration")
            # Validate plugin configuration
            required_types = ["string", "text", "image", "url", "file", "slug"]
            missing_types = []

            for field_type in required_types:
                if (
                    f"'{field_type}'" not in config_content
                    and f'"{field_type}"' not in config_content
                ):
                    missing_types.append(field_type)

            if missing_types:
                logging.warning(
                    f"⚠️  Plugin config missing field types: {missing_types}"
                )
                logging.warning(
                    "   Add these to fieldTypes array: ['string', 'text', 'image', 'url', 'file', 'slug']"
                )
        elif has_generated_import:
            logging.info("✅ Using generated i18n files approach")
        else:
            logging.warning(
                "⚠️  No internationalization configuration found in sanity.config.ts"
            )

    except Exception as e:
        logging.warning(f"⚠️  Could not validate sanity.config.ts: {e}")


def generate_all_files(all_schemas: List[dict], plan: dict):
    logging.info("\n--- 💾 PHASE 4: Generating All Project Files ---")
    if os.path.exists(SCHEMAS_DIR):
        shutil.rmtree(SCHEMAS_DIR)
    # --- MODIFIED: Only generate business schema directories
    for folder in ["documents", "objects"]:
        os.makedirs(os.path.join(SCHEMAS_DIR, folder), exist_ok=True)

    # --- DISABLED: i18n helper schema generation - using plugin approach instead
    # The sanity-plugin-internationalized-array provides better internationalization

    # 1. Write the AI-generated schemas
    all_schema_names = []
    for schema_data in all_schemas:
        schema_name = schema_data["name"]
        # --- MODIFIED: Simplified folder logic
        folder = "documents" if schema_data["type"] == "document" else "objects"
        file_name = f"{to_kebab_case(schema_name)}.ts"
        file_path = os.path.join(SCHEMAS_DIR, folder, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(schema_data["code"])
        logging.info(f"   ✅ Wrote {folder.upper()[:-1]} SCHEMA: {folder}/{file_name}")
        all_schema_names.append(schema_name)

    # 3. Generate the main index.ts file
    all_final_names = sorted(all_schema_names)
    imports = []
    for name in sorted(all_schema_names):
        schema_info = next((s for s in all_schemas if s["name"] == name), None)
        # --- MODIFIED: Simplified folder logic
        folder = "documents" if schema_info["type"] == "document" else "objects"
        imports.append(f"import {name} from './{folder}/{to_kebab_case(name)}'")

    index_content = f"// This file is auto-generated by the AI Schema Architect.\n{chr(10).join(imports)}\n\nexport const schemaTypes = [\n  {',\n  '.join(all_final_names)},\n];\n"
    with open(os.path.join(SCHEMAS_DIR, "index.ts"), "w", encoding="utf-8") as f:
        f.write(index_content)
    logging.info(f"   ✅ Wrote main schema index file: {SCHEMAS_DIR}/index.ts")


# --- 🚀 6. MAIN EXECUTION FLOW ---


def main():
    setup_logging()
    logging.info("🚀 AI Schema Architect (Improved) Initializing... 🚀")
    if not all([FIGMA_API_KEY, FIGMA_FILE_KEY, GEMINI_API_KEY]):
        logging.critical("❌ CONFIGURATION ERROR: Missing API keys in .env file.")
        sys.exit(1)

    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel(GEMINI_MODEL_NAME)

    sections = get_figma_page_sections()
    if not sections:
        logging.critical("❌ No Figma sections found. Check page/frame names. Exiting.")
        return

    plan = phase_one_architect_plan(sections, ai_model)
    if not plan:
        logging.critical(
            "❌ Failed to generate architectural plan. Check logs for details. Exiting."
        )
        return

    # --- MODIFIED: Simplified valid names set
    all_valid_names = set(plan.get("documents", [])) | set(plan.get("objects", []))
    logging.info(
        f"📋 Plan created. Valid schema names: {sorted(list(all_valid_names))}"
    )

    all_schema_data = []
    # --- MODIFIED: Simplified planned schemas list
    all_planned_schemas = [
        {"name": name, "type": "document"} for name in plan.get("documents", [])
    ] + [{"name": name, "type": "object"} for name in plan.get("objects", [])]

    for schema_info in all_planned_schemas:
        ts_code = phase_two_generate_schema_code(
            schema_info["name"], schema_info["type"], plan, sections, ai_model
        )
        if ts_code:
            all_schema_data.append(
                {
                    "name": schema_info["name"],
                    "type": schema_info["type"],
                    "code": ts_code,
                }
            )

    if not all_schema_data:
        logging.critical("❌ No schemas were generated in Phase 2. Exiting.")
        return

    logging.info("\n🔍 PHASE 3: Correcting and validating all generated code...")
    corrected_schemas = []
    for schema in all_schema_data:
        logging.info(f"  -> Correcting {schema['name']}...")
        # --- MODIFIED: Using the new, more powerful correction function with expected type
        corrected_code = correct_generated_code(
            schema["code"], all_valid_names, schema["type"]
        )

        # Validate the corrected code for any remaining issues
        issues = validate_generated_code(corrected_code, schema["name"])

        corrected_schemas.append({**schema, "code": corrected_code})
    logging.info("✅ PHASE 3: Code correction complete.")

    generate_all_files(corrected_schemas, plan)

    # Validate sanity.config.ts
    validate_sanity_config()

    logging.info("\n✨ All Done! High-Quality, Validated Schemas Generated! ✨")
    print("\n--- NEXT STEPS ---")
    print(
        f"1. A new directory '{SCHEMAS_DIR}' has been created with auto-corrected schemas."
    )
    print(
        "2. The script used improved prompts and a robust auto-correction phase to prevent common errors."
    )
    print(
        "3. **Internationalization (i18n) support via sanity-plugin-internationalized-array (Recommended).**"
    )
    print("\n4. **SETUP INTERNATIONALIZATION:**")
    print("   a. Install: `npm install sanity-plugin-internationalized-array`")
    print("   b. In sanity.config.ts, add to plugins array:")
    print("      ```js")
    print(
        "      import {internationalizedArray} from 'sanity-plugin-internationalized-array'"
    )
    print("      ")
    print("      plugins: [")
    print("        // ... other plugins")
    print("        internationalizedArray({")
    print("          languages: [")
    print("            {id: 'en', title: 'English'},")
    print("            {id: 'hin', title: 'Hindi'}, // Add your languages")
    print("          ],")
    print("          defaultLanguages: ['en'],")
    print("          fieldTypes: ['string', 'text', 'image', 'url', 'file', 'slug'],")
    print("        }),")
    print("      ]")
    print("      ```")
    print(
        f"\n5. Copy the entire generated `{SCHEMAS_DIR}` directory into your Sanity project."
    )
    print(
        "6. In `sanity.config.ts`, import `schemaTypes` and set `schema: { types: schemaTypes }`."
    )
    print(
        "7. Start Sanity Studio to see your professionally structured, internationalized schema!"
    )
    print(
        "\n🌍 You should now see language tabs (English/Hindi) on all internationalized fields!"
    )


if __name__ == "__main__":
    main()
