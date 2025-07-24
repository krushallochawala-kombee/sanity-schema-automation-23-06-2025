# import os
# import re
# import sys
# import time
# import json
# import logging
# import shutil
# from typing import Dict, Any, List, Optional
# import google.generativeai as genai
# import requests
# from dotenv import load_dotenv
# from json_repair import loads as json_repair_loads
# from inflection import singularize

# # --- ⚙️ 1. CONFIGURATION ---
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
# )
# load_dotenv()

# # --- MAKE SURE TO SET YOUR KEYS IN A .env FILE OR HERE ---
# FIGMA_API_KEY = os.getenv("FIGMA_API_KEY")
# FIGMA_FILE_KEY = os.getenv("FIGMA_FILE_KEY")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# # --- Settings ---
# SCHEMAS_DIR = "schemaTypes"
# FIGMA_PAGE_NAME = "Page 1"
# FIGMA_MAIN_FRAME_NAME = "Desktop"
# GEMINI_MODEL_NAME = "gemini-2.5-flash"

# # --- 🛠️ 2. HELPER FUNCTIONS ---
# def to_pascal_case(text: str) -> str:
#     return "".join(word.capitalize() for word in re.split(r"[\s_-]+", text))

# def to_camel_case(text: str) -> str:
#     pascal = to_pascal_case(text)
#     return pascal[0].lower() + pascal[1:] if pascal else ""

# def to_kebab_case(text: str) -> str:
#     s1 = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', text)
#     return re.sub(r'([A-Z])', r'-\1', s1).lstrip('-').lower()

# def extract_json_from_response(text: str) -> Optional[dict]:
#     if not text:
#         logging.warning("Received empty text from AI.")
#         return None
#     match = re.search(r"```(?:json)?\s*(\{[\s\S]+?\})\s*```", text, re.DOTALL)
#     json_str = match.group(1).strip() if match else text.strip()
#     try:
#         return json_repair_loads(json_str)
#     except Exception as e:
#         logging.error(f"JSON repair failed: {e}\nResponse was:\n{text}")
#         return None

# # --- 🖼️ 3. FIGMA DATA & SUMMARIZATION ---
# def get_figma_document_data() -> Optional[dict]:
#     if not FIGMA_API_KEY or not FIGMA_FILE_KEY:
#         logging.error("Figma API token or file ID missing.")
#         return None
#     url = f"https://api.figma.com/v1/files/{FIGMA_FILE_KEY}"
#     headers = {"X-Figma-Token": FIGMA_API_KEY}
#     try:
#         response = requests.get(url, headers=headers, timeout=60)
#         response.raise_for_status()
#         logging.info("✅ Fetched Figma file data successfully.")
#         return response.json()
#     except requests.RequestException as e:
#         logging.error(f"Error fetching Figma file data: {e}")
#         return None

# def clean_node_for_ai(node: dict, depth=0, max_depth=7) -> Optional[dict]:
#     if not node or depth > max_depth:
#         return None
#     cleaned = {"name": node.get("name", "Untitled"), "type": node.get("type")}
#     if node.get("type") == "TEXT":
#         cleaned["characters"] = node.get("characters")
#     if "children" in node:
#         children = [
#             clean_node_for_ai(child, depth + 1, max_depth)
#             for child in node.get("children", [])
#             if child.get("type") in ["FRAME", "COMPONENT", "INSTANCE", "TEXT", "VECTOR", "GROUP", "RECTANGLE"]
#         ]
#         cleaned_children = [c for c in children if c]
#         if cleaned_children:
#             cleaned["children"] = cleaned_children
#     if any(f.get("type") == "IMAGE" for f in node.get("fills", [])):
#         cleaned["isImagePlaceholder"] = True
#     return cleaned

# def get_figma_page_sections() -> List[dict]:
#     logging.info(f"📄 Fetching sections from Figma frame '{FIGMA_MAIN_FRAME_NAME}' on page '{FIGMA_PAGE_NAME}'...")
#     figma_data = get_figma_document_data()
#     if not figma_data: return []
#     try:
#         document = figma_data["document"]
#         target_page = next((p for p in document["children"] if p.get("name") == FIGMA_PAGE_NAME), None)
#         if not target_page: raise ValueError(f"Page '{FIGMA_PAGE_NAME}' not found.")
#         main_frame = next((f for f in target_page["children"] if f.get("type") == "FRAME" and f.get("name") == FIGMA_MAIN_FRAME_NAME), None)
#         if not main_frame: raise ValueError(f"Main frame '{FIGMA_MAIN_FRAME_NAME}' not found.")
#         sections = [{"name": node.get("name"), "node": node} for node in main_frame["children"] if node.get("type") in ["FRAME", "COMPONENT", "INSTANCE"] and node.get("name")]
#         if not sections: raise ValueError(f"No sections found in '{FIGMA_MAIN_FRAME_NAME}'.")
#         logging.info(f"✅ Found {len(sections)} top-level page sections.")
#         return sections
#     except (ValueError, KeyError, StopIteration) as e:
#         logging.error(f"❌ Figma Error: {e}")
#         return []

# # --- 🤖 4. AI ARCHITECT (DEEP ANALYSIS) ---
# def phase_one_architect_plan(sections: List[dict], model) -> Optional[dict]:
#     logging.info("🤖 PHASE 1: Creating architectural plan from Figma JSON...")
#     sections_summary = [{"name": section["name"], "structure": clean_node_for_ai(section["node"])} for section in sections]
#     prompt = f"""
# You are a top-tier Sanity.io Lead Architect. Analyze the lightweight JSON representation of a Figma design and create a high-level, scalable, and DRY schema plan.
# **Rules:**
# 1.  `documents` for top-level data. `objects` for components.
# 2.  For repeating lists (e.g., "Team Members"), define a singular `document` (`teamMember`) and a container `object` (`teamSection`).
# 3.  Plan a `siteSettings` document for global content like headers/footers.
# 4.  Identify reusable objects like `ctaButton`, `link`, `seo`.
# 5.  Always include a `page` document. Do not name anything `block`.
# **Figma JSON:**
# {json.dumps(sections_summary, indent=2)}
# **Output:** Return ONLY a valid JSON object with `documents`, `objects`, and `blocks` keys with camelCase names.
# """
#     max_retries = 3
#     for attempt in range(max_retries):
#         try:
#             logging.info(f"  Attempting to generate plan (Attempt {attempt + 1}/{max_retries})...")
#             response = model.generate_content(prompt)
#             raw_plan = extract_json_from_response(response.text)

#             if not raw_plan:
#                 raise ValueError("AI response did not contain valid JSON.")

#             plan = {}
#             for key in ["documents", "objects", "blocks"]:
#                 items = raw_plan.get(key, [])
#                 processed_names = []
#                 for item in items:
#                     name = item.get("name") if isinstance(item, dict) else item
#                     if name and isinstance(name, str):
#                         processed_names.append(to_camel_case(name))
#                 plan[key] = processed_names

#             if "page" not in plan["documents"]:
#                 plan["documents"].append("page")

#             logging.info(f"✅ PHASE 1: Architectural plan received and sanitized: {plan}")
#             return plan
#         except Exception as e:
#             logging.warning(f"  Phase 1, Attempt {attempt + 1} failed: {e}")
#             if attempt < max_retries - 1:
#                 time.sleep(2)
#             else:
#                 logging.error(f"❌ Gemini Error during Phase 1 after {max_retries} attempts.")
#                 return None
#     return None

# def phase_two_generate_field_data(
#     schema_name: str, classification: str, plan: dict, sections: List[dict], model
# ) -> Optional[dict]:
#     logging.info(f"  🤖 PHASE 2: Generating field data for '{schema_name}' ({classification})...")
#     context = f"Architectural Plan: Documents: {plan.get('documents', [])}, Objects: {plan.get('objects', [])}"
#     relevant_section = next((clean_node_for_ai(s["node"]) for s in sections if to_camel_case(s["name"]) == schema_name), None)
    
#     # --- NEW: High-Fidelity Logic ---
#     if relevant_section:
#         structure_info = f"""
# **Figma Structure to Analyze for '{schema_name}':**
# {json.dumps(relevant_section, indent=2)}
# """
#     else:
#         # If no direct Figma structure exists, provide very specific, minimal instructions.
#         structure_info = (
#             f"**CRITICAL INSTRUCTION:** No direct Figma structure was found for '{schema_name}'.\n"
#             "You MUST generate a minimal, logical schema based on its name. DO NOT INVENT extra fields.\n"
#             "Examples:\n"
#             "- For `link`: Create fields for `title` (string) and `url` (url).\n"
#             "- For `ctaButton`: Create fields for `text` (string) and `link` (a reference of type `link`).\n"
#             "- For `siteSettings`: Create fields for `siteTitle` (string), `logo` (image), and perhaps `mainNav` (an array of `link`).\n"
#             "- For `seo`: Create fields for `metaTitle` (string), `metaDescription` (text), and `shareImage` (image)."
#         )

#     page_builder_objects = [name for name in plan.get("objects", []) if name not in ["ctaButton", "link", "seo", "imageWithAlt"]]
    
#     prompt = f"""
# You are a precise data mapping engine. Your ONLY job is to convert the provided information into a valid Sanity.io schema JSON.
# You MUST follow these rules with extreme precision:

# 1.  **Strict Fidelity Rule (NO HALLUCINATIONS):** You MUST NOT invent fields. Every field you create must correspond directly to a named layer, text content, or image placeholder in the provided 'Figma Structure'. If the structure has a text node named "Subtitle", you create a field named "subtitle". If it's an image placeholder, create an "image" field. Do not add fields for "color", "font-size", or other style attributes.

# 2.  **Handling Abstract Schemas:** If the instruction is "No direct Figma structure was found", you MUST follow the provided examples precisely and create only the minimal fields requested for that schema type.

# 3.  **Reference Rule:** Consult the master plan: {context}. If you are building a container object (e.g., `serviceGrid`) and a corresponding data document exists in the plan (e.g., `service`), the field MUST be an array of `reference`s. Example: `{{"name": "services", "type": "array", "of": [{{"type": "reference", "to": [{{"type": "service"}}]}}]}}`.

# 4.  **Internationalization (i18n):** For any user-facing content (fields of type `string`, `text`, `image`, etc.), add the property `"i18n": true`.

# 5.  **Page Builder:** If `schema_name` is `page`, you MUST include a `pageBuilder` array field, with its `of` property referencing these objects: `{page_builder_objects}`.

# **Output Format:** Respond with a SINGLE, valid JSON object for the schema '{schema_name}'.

# {structure_info}
# """
#     try:
#         time.sleep(1.2)
#         response = model.generate_content(prompt)
#         data = extract_json_from_response(response.text)
#         if not data or not isinstance(data.get("fields"), list):
#             raise ValueError(f"Phase 2 response for '{schema_name}' was malformed.")
#         data.update({"name": to_camel_case(schema_name), "title": to_pascal_case(data.get("title", schema_name)), "type": classification})
#         logging.info(f"    ✅ PHASE 2: Field data for '{schema_name}' structured with high fidelity.")
#         return data
#     except Exception as e:
#         logging.error(f"❌ Gemini Error during Phase 2 for '{schema_name}': {e}\nResponse: {getattr(response, 'text', 'No response text')}")
#         return None

# # --- ✨ 5. SANITY SCHEMA COMPILER & VALIDATOR ---
# def correct_and_validate_schemas(all_schemas: List[Dict[str, Any]], plan: Dict[str, List[str]]):
#     logging.info("\n--- 🧐 PHASE 3: Compiling and Validating Schemas ---")
#     all_valid_names = set(plan.get("documents", []) + plan.get("objects", []) + plan.get("blocks", []))
#     document_names = set(plan.get("documents", []))
#     for schema in all_schemas:
#         if not schema.get("fields"): continue
#         for field in schema.get("fields", []):
#             field_type_camel = to_camel_case(field.get("type", ""))
#             if field_type_camel in all_valid_names and field["type"] != field_type_camel:
#                 logging.info(f"    🔧 CORRECTING CASING: In '{schema['name']}', changing field type '{field['type']}' to '{field_type_camel}'.")
#                 field["type"] = field_type_camel
#             if field.get("type") == "array" and field.get("of") and field["of"][0].get("type") == "object":
#                 field_name_singular = singularize(field.get("name", ""))
#                 if field_name_singular in document_names:
#                     logging.info(f"    🔧 CORRECTING GRID RULE: In '{schema['name']}', changing field '{field['name']}' to array of references to '{field_name_singular}'.")
#                     field['of'] = [{'type': 'reference', 'to': [{'type': field_name_singular}]}]
#     logging.info("--- ✅ PHASE 3: Schema validation and correction complete. ---")

# def generate_ts_code(schema_def: dict) -> str:
#     """Generates clean, valid TypeScript code, with i18n logic."""
#     def format_field(field_def, indent_level=2):
#         indent = "  " * indent_level
#         name = to_camel_case(field_def.get("name", ""))
#         title = field_def.get("title")
#         if not name and title: name = to_camel_case(title)
#         elif not name:
#             logging.error(f"FATAL: Field in schema '{schema_def.get('name')}' is missing a 'name'. Skipping. Details: {field_def}")
#             return ""
#         if not title: title = to_pascal_case(name)

#         original_type = field_def.get("type", "string")
#         is_i18n = field_def.get("i18n", False)
#         final_type = original_type
        
#         if is_i18n and original_type in ["string", "text", "image", "url", "file", "slug"]:
#             final_type = f"internationalizedArray{original_type.capitalize()}"

#         ts_parts = [f"name: '{name}'", f"title: '{title}'", f"type: '{final_type}'"]
        
#         if "fields" in field_def and original_type in ["object", "image", "file"] and not is_i18n:
#             field_content = "".join([format_field(f, indent_level + 1) for f in field_def.get("fields", [])])
#             ts_parts.append(f"fields: [\n{field_content}{indent}]")

#         if "of" in field_def and original_type == "array":
#             of_content_list = []
#             for item in field_def.get("of", []):
#                 if item.get("type") == "object" and "fields" in item:
#                     inline_fields = "".join([format_field(f, indent_level + 2) for f in item.get("fields", [])])
#                     of_content_list.append(f"{indent}  {{\n{indent}    type: 'object',\n{indent}    fields: [\n{inline_fields}{indent}    ]\n{indent}  }}")
#                 else:
#                     of_content_list.append(f"{indent}  {json.dumps(item)}")
#             ts_parts.append(f"of: [\n{','.join(of_content_list)}\n{indent}]")
        
#         if "to" in field_def: ts_parts.append(f"to: {json.dumps(field_def['to'])}")
#         if "options" in field_def: ts_parts.append(f"options: {json.dumps(field_def['options'])}")

#         return f"{indent}defineField({{\n{indent}  " + f",\n{indent}  ".join(ts_parts) + f"\n{indent}}}),\n"

#     field_ts_strings = "".join([format_field(field) for field in schema_def.get("fields", [])])
#     return f"""import {{defineType, defineField}} from 'sanity'

# export default defineType({{
#   name: '{schema_def.get('name', 'unnamed')}',
#   title: '{schema_def.get('title', 'Unnamed')}',
#   type: '{schema_def.get('type', 'object')}',
#   fields: [
# {field_ts_strings}
#   ],
#   {f"preview: {{ select: {{ title: 'title' }} }}," if schema_def.get('type') == 'document' else ''}
# }})
# """

# def generate_all_files(all_schemas: List[dict], plan: dict):
#     logging.info("\n--- 💾 PHASE 4: Generating All Project Files (with Corrected Tabbed i18n) ---")
#     if os.path.exists(SCHEMAS_DIR):
#         shutil.rmtree(SCHEMAS_DIR)
#         logging.info(f"Removed existing directory: {SCHEMAS_DIR}")

#     for folder in ["documents", "objects", "blocks"]:
#         os.makedirs(os.path.join(SCHEMAS_DIR, folder), exist_ok=True)
    
#     i18n_plugin_dir = os.path.join(SCHEMAS_DIR, "plugins", "i18n")
#     os.makedirs(i18n_plugin_dir, exist_ok=True)
#     i18n_schema_names = []

#     i18n_type_template = """import {{defineType}} from 'sanity'

# // This file is auto-generated by the AI-Schema-Generator
# // It is used by the sanity-plugin-internationalized-array to render a tabbed UI

# export default defineType({{
#   name: 'internationalizedArray{type_pascal}',
#   type: 'array',
#   title: 'Internationalized {type_pascal}',
#   of: [{{ type: '{type_camel}' }}],
#   options: {{
#     layout: 'tabs',
#   }},
# }})
# """

#     for t in ["String", "Text", "Image", "File", "Url", "Slug"]:
#         file_path = os.path.join(i18n_plugin_dir, f"{t.lower()}.ts")
#         file_content = i18n_type_template.format(type_pascal=t, type_camel=t.lower())
#         with open(file_path, "w", encoding="utf-8") as f:
#             f.write(file_content.strip())
#         logging.info(f"   ✅ Wrote I18N HELPER: plugins/i18n/{t.lower()}.ts (with Tabs UI)")
#         i18n_schema_names.append(f"internationalizedArray{t}")

#     schemas_by_name = {s['name']: s for s in all_schemas}
#     user_schema_names = []
#     for schema_name, schema_data in schemas_by_name.items():
#         folder = "objects"
#         if schema_data.get("type") == "document": folder = "documents"
#         elif schema_name in plan.get("blocks", []): folder = "blocks"
#         file_path = os.path.join(SCHEMAS_DIR, folder, f"{to_kebab_case(schema_name)}.ts")
#         try:
#             with open(file_path, "w", encoding="utf-8") as f: f.write(generate_ts_code(schema_data))
#             logging.info(f"   ✅ Wrote {folder.upper()}: {folder}/{to_kebab_case(schema_name)}.ts")
#             user_schema_names.append(schema_name)
#         except Exception as e:
#             logging.error(f"   ❌ FAILED to write {file_path}. Reason: {e}")

#     all_schema_names = sorted(user_schema_names + i18n_schema_names)
#     imports = []
#     for name in sorted(user_schema_names):
#         schema_info = schemas_by_name.get(name)
#         folder = "objects"
#         if schema_info.get("type") == "document": folder = "documents"
#         elif name in plan.get("blocks", []): folder = "blocks"
#         imports.append(f"import {name} from './{folder}/{to_kebab_case(name)}'")
    
#     for name in sorted(i18n_schema_names):
#         type_name = name.replace("internationalizedArray", "").lower()
#         imports.append(f"import {name} from './plugins/i18n/{type_name}'")

#     with open(os.path.join(SCHEMAS_DIR, "index.ts"), "w", encoding="utf-8") as f:
#         f.write(f"// This file is auto-generated by the AI Schema Architect.\n{chr(10).join(imports)}\n\nexport const schemaTypes = [\n  {', '.join(all_schema_names)}\n];\n")
#     logging.info(f"   ✅ Wrote main schema index file: {SCHEMAS_DIR}/index.ts")


# # --- 🚀 6. MAIN EXECUTION FLOW ---
# def main():
#     logging.info("🚀 AI Schema Architect (v15 - High Fidelity) 🚀")
#     if not all([FIGMA_API_KEY, FIGMA_FILE_KEY, GEMINI_API_KEY]):
#         logging.critical("❌ CONFIGURATION ERROR: Missing required API keys in .env file.")
#         sys.exit(1)

#     genai.configure(api_key=GEMINI_API_KEY)
#     ai_model = genai.GenerativeModel(GEMINI_MODEL_NAME)

#     sections = get_figma_page_sections()
#     if not sections:
#         logging.critical("❌ No Figma sections found. Check FIGMA_FILE_KEY, FIGMA_PAGE_NAME, and FIGMA_MAIN_FRAME_NAME. Exiting.")
#         return

#     plan = phase_one_architect_plan(sections, ai_model)
#     if not plan:
#         logging.critical("❌ Failed to generate architectural plan. Exiting.")
#         return

#     all_schema_data = []
#     for classification in ["documents", "objects", "blocks"]:
#         for name in plan.get(classification, []):
#             final_classification = "object" if classification == "blocks" else classification.rstrip("s")
#             schema_data = phase_two_generate_field_data(name, final_classification, plan, sections, ai_model)
#             if schema_data: all_schema_data.append(schema_data)

#     if not all_schema_data:
#         logging.critical("❌ No schemas were generated in Phase 2. Exiting.")
#         return

#     correct_and_validate_schemas(all_schema_data, plan)
#     generate_all_files(all_schema_data, plan)

#     logging.info("\n✨ All Done! ✨")
#     print("\n--- NEXT STEPS ---")
#     print(f"1. A new directory '{SCHEMAS_DIR}' has been created with a fully integrated i18n setup for a **Tabs UI**.")
#     print("2. **CRITICAL:** Install the required Sanity plugin:")
#     print("   `npm install sanity-plugin-internationalized-array` (or pnpm/yarn)")
#     print("\n3. **CRITICAL: In `sanity.config.ts`**, configure the plugin. This is required for it to work!")
#     print("   // In your plugins array, add:")
#     print("   internationalizedArray({")
#     print("     languages: [{id: 'en', title: 'English'}, {id: 'hin', title: 'Hindi'}],")
#     print("     defaultLanguage: 'en',")
#     print("     fieldTypes: ['string', 'text', 'image', 'file', 'url', 'slug'],")
#     print("   })")
#     print(f"\n4. Copy the entire generated `{SCHEMAS_DIR}` directory into your Sanity project.")
#     print("5. In `sanity.config.ts`, import `schemaTypes` and set `schema: { types: schemaTypes }`.")
#     print("6. Start Sanity Studio to see your precise, tabbed, multi-language schema!")

# if __name__ == "__main__":
#     try:
#         import inflection
#     except ImportError:
#         print("\nERROR: Required library `inflection` not found. Please run: pip install inflection\n")
#         sys.exit(1)
#     main()

























# import os
# import re
# import sys
# import time
# import json
# import logging
# import shutil
# from typing import Dict, Any, List, Optional
# import google.generativeai as genai
# import requests
# from dotenv import load_dotenv
# from json_repair import loads as json_repair_loads
# from inflection import singularize

# # --- ⚙️ 1. CONFIGURATION ---
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
# )
# load_dotenv()

# # --- MAKE SURE TO SET YOUR KEYS IN A .env FILE OR HERE ---
# FIGMA_API_KEY = os.getenv("FIGMA_API_KEY")
# FIGMA_FILE_KEY = os.getenv("FIGMA_FILE_KEY")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# # --- Settings ---
# SCHEMAS_DIR = "schemaTypes"
# FIGMA_PAGE_NAME = "Page 1"
# FIGMA_MAIN_FRAME_NAME = "Homepage"
# GEMINI_MODEL_NAME = "gemini-2.5-flash" # Using a powerful model is key

# # --- 🛠️ 2. HELPER FUNCTIONS ---
# def to_pascal_case(text: str) -> str:
#     return "".join(word.capitalize() for word in re.split(r"[\s_-]+", text))

# def to_camel_case(text: str) -> str:
#     pascal = to_pascal_case(text)
#     return pascal[0].lower() + pascal[1:] if pascal else ""

# def to_kebab_case(text: str) -> str:
#     s1 = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', text)
#     return re.sub(r'([A-Z])', r'-\1', s1).lstrip('-').lower()

# def extract_json_from_response(text: str) -> Optional[dict]:
#     if not text:
#         logging.warning("Received empty text from AI.")
#         return None
#     match = re.search(r"```(?:json)?\s*(\{[\s\S]+?\})\s*```", text, re.DOTALL)
#     json_str = match.group(1).strip() if match else text.strip()
#     try:
#         return json_repair_loads(json_str)
#     except Exception as e:
#         logging.error(f"JSON repair failed: {e}\nResponse was:\n{text}")
#         return None

# # --- 🖼️ 3. FIGMA DATA & SUMMARIZATION ---
# def get_figma_document_data() -> Optional[dict]:
#     if not FIGMA_API_KEY or not FIGMA_FILE_KEY:
#         logging.error("Figma API token or file ID missing.")
#         return None
#     url = f"https://api.figma.com/v1/files/{FIGMA_FILE_KEY}"
#     headers = {"X-Figma-Token": FIGMA_API_KEY}
#     try:
#         response = requests.get(url, headers=headers, timeout=60)
#         response.raise_for_status()
#         logging.info("✅ Fetched Figma file data successfully.")
#         return response.json()
#     except requests.RequestException as e:
#         logging.error(f"Error fetching Figma file data: {e}")
#         return None

# def clean_node_for_ai(node: dict, depth=0, max_depth=8) -> Optional[dict]:
#     if not node or depth > max_depth:
#         return None
#     cleaned = {"name": node.get("name", "Untitled"), "type": node.get("type")}
#     if node.get("type") == "TEXT":
#         cleaned["characters"] = node.get("characters")
#     if any(f.get("type") == "IMAGE" for f in node.get("fills", [])):
#         cleaned["isImagePlaceholder"] = True
    
#     if "children" in node:
#         children = [
#             clean_node_for_ai(child, depth + 1, max_depth)
#             for child in node.get("children", [])
#         ]
#         cleaned_children = [c for c in children if c]
#         if cleaned_children:
#             cleaned["children"] = cleaned_children
#     return cleaned

# def classify_figma_sections() -> Dict[str, List[Dict]]:
#     logging.info(f"📄 Fetching and classifying sections from Figma frame '{FIGMA_MAIN_FRAME_NAME}'...")
#     figma_data = get_figma_document_data()
#     if not figma_data: return {}

#     classified_sections = {"header": [], "footer": [], "page_sections": []}
#     try:
#         document = figma_data["document"]
#         target_page = next((p for p in document["children"] if p.get("name") == FIGMA_PAGE_NAME), None)
#         if not target_page: raise ValueError(f"Page '{FIGMA_PAGE_NAME}' not found.")
#         main_frame = next((f for f in target_page["children"] if f.get("type") == "FRAME" and f.get("name") == FIGMA_MAIN_FRAME_NAME), None)
#         if not main_frame: raise ValueError(f"Main frame '{FIGMA_MAIN_FRAME_NAME}' not found.")
        
#         all_sections = [
#             {"name": node.get("name"), "node": node} 
#             for node in main_frame["children"] 
#             if node.get("type") in ["FRAME", "COMPONENT", "INSTANCE"] and node.get("name")
#         ]

#         if not all_sections:
#             raise ValueError(f"No sections (frames/components) found in '{FIGMA_MAIN_FRAME_NAME}'.")

#         for section in all_sections:
#             name_lower = section["name"].lower()
#             if 'header' in name_lower:
#                 classified_sections["header"].append(section)
#             elif 'footer' in name_lower:
#                 classified_sections["footer"].append(section)
#             else:
#                 classified_sections["page_sections"].append(section)
        
#         logging.info(f"✅ Classified sections: {len(classified_sections['header'])} Header(s), {len(classified_sections['footer'])} Footer(s), {len(classified_sections['page_sections'])} Page Section(s).")
#         return classified_sections
#     except (ValueError, KeyError, StopIteration) as e:
#         logging.error(f"❌ Figma Error: {e}")
#         return {}

# # --- 🤖 4. AI ARCHITECT (DEEP ANALYSIS) ---
# def phase_one_architect_plan(sections: List[dict], model) -> Optional[dict]:
#     logging.info("🤖 PHASE 1: Creating high-level architectural plan...")
#     sections_summary = [{"name": section["name"], "structure_overview": clean_node_for_ai(section["node"], max_depth=3)} for section in sections]
#     prompt = f"""
# You are a top-tier Sanity.io Lead Architect. Your task is to analyze the high-level structure of a Figma design and create a robust, scalable, and DRY schema plan.

# **Architectural Rules (MANDATORY):**
# 1.  **Documents vs. Objects:**
#     -   `documents` are for top-level, queryable data collections (e.g., `post`, `service`, `teamMember`, `page`, `siteSettings`). These represent the core "data" of the site.
#     -   `objects` are for structural components used within documents (e.g., `heroSection`, `ctaButton`, `testimonialGrid`). These represent the "layout" of a page.

# 2.  **The Grid/List Rule (CRITICAL for Reusability):** When you see a section that visually contains a list of repeating items (e.g., a "Team" section with multiple "Team Member Card" children), you MUST do two things:
#     a.  Define a **singular `document`** for the underlying data item (e.g., `teamMember`, `service`, `faqItem`).
#     b.  Define an **`object`** for the page section that will display these items (e.g., `teamSection`, `serviceGrid`). This object will later contain an array of `reference`s to the documents.

# 3.  **Global Content Rule:** If you infer a global "Header" or "Footer", you MUST include a `siteSettings` document in your plan to hold their content.

# 4.  **Always Include `page`:** A `page` document is mandatory for building pages.

# **Figma Structure Overview:**
# {json.dumps(sections_summary, indent=2)}

# **Your Output:**
# Return ONLY a valid JSON object with `documents` and `objects` keys. The values must be lists of unique, camelCase schema names. Do not add any explanation or markdown.
# """
#     max_retries = 3
#     for attempt in range(max_retries):
#         try:
#             logging.info(f"  Attempting to generate plan (Attempt {attempt + 1}/{max_retries})...")
#             response = model.generate_content(prompt)
#             raw_plan = extract_json_from_response(response.text)
            
#             if not raw_plan:
#                  raise ValueError("AI response did not contain valid JSON.")

#             plan = {}
#             for key in ["documents", "objects"]:
#                 items = raw_plan.get(key, [])
#                 processed_names = []
#                 for item in items:
#                     name = item if isinstance(item, str) else item.get("name")
#                     if name and isinstance(name, str):
#                         processed_names.append(to_camel_case(name))
#                 plan[key] = sorted(list(set(processed_names)))
            
#             if "page" not in plan["documents"]:
#                 plan["documents"].append("page")
            
#             logging.info(f"✅ PHASE 1: Architectural plan received and sanitized: {plan}")
#             return plan
#         except Exception as e:
#             logging.warning(f"  Phase 1, Attempt {attempt + 1} failed: {e}")
#             if attempt < max_retries - 1:
#                 time.sleep(2)
#             else:
#                 logging.error(f"❌ Gemini Error during Phase 1 after {max_retries} attempts.")
#                 return None
#     return None

# def phase_two_generate_field_data(
#     schema_name: str, 
#     classification: str, 
#     plan: dict, 
#     nodes_to_analyze: List[Dict],
#     model
# ) -> Optional[dict]:
#     logging.info(f"  🤖 PHASE 2: Generating field data for '{schema_name}' ({classification})...")
    
#     if nodes_to_analyze:
#         # **ENHANCEMENT**: Always provide a single, representative node structure to the AI
#         # This prevents ambiguity where the AI might return a list if it receives a list.
#         representative_node = clean_node_for_ai(nodes_to_analyze[0]['node'])
#         structure_info = f"**Figma Structure to Analyze for '{schema_name}':**\n{json.dumps(representative_node, indent=2)}"
#     else:
#         structure_info = (
#             f"**CRITICAL INSTRUCTION:** No direct Figma structure was found for '{schema_name}'. Generate a minimal, logical schema based on its name. DO NOT INVENT extra fields. Example: for `link`, create `title` and `url` fields."
#         )

#     page_builder_objects = [name for name in plan.get("objects", []) if name not in plan.get("documents", []) and name != 'siteSettings']
    
#     prompt = f"""
# You are a precise data mapping engine. Your ONLY job is to convert the provided Figma JSON into a valid Sanity.io schema, strictly following the master plan.

# **Master Architectural Plan (You MUST obey this):**
# -   **Documents:** {plan.get('documents', [])}
# -   **Objects:** {plan.get('objects', [])}

# **Rules of Engagement (MANDATORY):**
# 1.  **Strict Fidelity Rule (NO HALLUCINATIONS):** You MUST NOT invent fields. Perform a 1-to-1 mapping. Every field you create must correspond DIRECTLY to a named layer, text content, or image placeholder in the provided 'Figma Structure'. If a text node is named "Main Heading", create a field named "mainHeading". You are FORBIDDEN from adding fields for styling or any property not visible as content.

# 2.  **Reference Rule (CRITICAL):** You MUST adhere to the Master Plan. If you are building a container object (e.g., `teamSection`) and the plan includes a corresponding data document (e.g., `teamMember`), the field for the items MUST be an `array` of `reference`s.
#     -   **Correct Example:** `{{"name": "members", "title": "Members", "type": "array", "of": [{{"type": "reference", "to": [{{"type": "teamMember"}}]}}]}}`
#     -   **INCORRECT:** Do NOT define the fields for a `teamMember` (like name, role) inside the `teamSection`.

# 3.  **Validation Rule:** For essential fields that must not be empty (like a main title, a hero image), you MUST add the property `"validation": "required"` to that field's definition. Omit it for optional fields.

# 4.  **Internationalization (i18n):** For any user-facing content (fields of type `string`, `text`, `image`), you MUST add the property `"i18n": true`.

# 5.  **Page Builder:** If `schema_name` is `page`, you MUST include a `pageBuilder` array field. Its `of` property must be an array of `type` references to these objects from the plan: `{page_builder_objects}`.

# **Your Task:**
# Create the schema JSON for '{schema_name}'. Your output must be a SINGLE, valid JSON OBJECT.

# {structure_info}
# """
#     try:
#         time.sleep(1.5) # Rate limiting
#         response = model.generate_content(prompt)
#         data = extract_json_from_response(response.text)

#         # --- CORE BUG FIX ---
#         # The original error "list object has no attribute 'get'" happened here.
#         # This new block explicitly checks if the AI returned a dictionary. If not,
#         # it fails gracefully instead of crashing the script.
#         if not isinstance(data, dict):
#             raise ValueError(f"AI response for '{schema_name}' was not a valid JSON object. Got type: {type(data)}")
        
#         # Ensure the 'fields' key exists, even if it's empty.
#         if "fields" not in data or not isinstance(data.get("fields"), list):
#             logging.warning(f"Response for '{schema_name}' lacked a 'fields' array. Assuming no fields.")
#             data["fields"] = []
        
#         data.update({"name": to_camel_case(schema_name), "title": to_pascal_case(data.get("title", schema_name)), "type": classification})
#         logging.info(f"    ✅ PHASE 2: Field data for '{schema_name}' structured with high fidelity.")
#         return data
#     except Exception as e:
#         logging.error(f"❌ Gemini Error during Phase 2 for '{schema_name}': {e}\nResponse: {getattr(response, 'text', 'No response text')}")
#         return None

# # --- ✨ 5. SANITY SCHEMA COMPILER & FILE GENERATOR ---
# def correct_and_validate_schemas(all_schemas: List[Dict[str, Any]], plan: Dict[str, List[str]]):
#     logging.info("\n--- 🧐 PHASE 3: Compiling and Validating Schemas (Safety Net) ---")
#     all_valid_names = set(plan.get("documents", []) + plan.get("objects", []))
#     document_names = set(plan.get("documents", []))
#     for schema in all_schemas:
#         if not isinstance(schema, dict) or not schema.get("fields"): continue
#         for field in schema.get("fields", []):
#             field_type_camel = to_camel_case(field.get("type", ""))
#             if field_type_camel in all_valid_names and field["type"] != field_type_camel:
#                 logging.info(f"    🔧 CORRECTING CASING: In '{schema['name']}', changing field type '{field['type']}' to '{field_type_camel}'.")
#                 field["type"] = field_type_camel
#             if field.get("type") == "array" and field.get("of") and field["of"][0].get("type") == "object":
#                 field_name_singular = singularize(field.get("name", ""))
#                 if field_name_singular in document_names:
#                     logging.info(f"    🔧 CORRECTING GRID RULE: In '{schema['name']}', changing field '{field['name']}' to array of references to '{field_name_singular}'.")
#                     field['of'] = [{'type': 'reference', 'to': [{'type': field_name_singular}]}]
#     logging.info("--- ✅ PHASE 3: Schema validation and correction complete. ---")

# def generate_ts_code(schema_def: dict) -> str:
#     def format_field(field_def, indent_level=2):
#         indent = "  " * indent_level
#         name = to_camel_case(field_def.get("name", ""))
#         title = field_def.get("title")
#         if not name and title: name = to_camel_case(title)
#         elif not name:
#             logging.error(f"FATAL: Field in schema '{schema_def.get('name')}' is missing a 'name'. Skipping.")
#             return ""
#         if not title: title = to_pascal_case(name)

#         original_type = field_def.get("type", "string")
#         is_i18n = field_def.get("i18n", False)
#         final_type = original_type
        
#         if is_i18n and original_type in ["string", "text", "image", "url", "file", "slug"]:
#             final_type = f"internationalizedArray{original_type.capitalize()}"

#         ts_parts = [f"name: '{name}'", f"title: '{title}'", f"type: '{final_type}'"]
        
#         if field_def.get("validation") == "required":
#             ts_parts.append("validation: (Rule) => Rule.required()")
            
#         if "fields" in field_def and original_type in ["object", "image", "file"] and not is_i18n:
#             field_content = "".join([format_field(f, indent_level + 1) for f in field_def.get("fields", [])])
#             ts_parts.append(f"fields: [\n{field_content}{indent}]")

#         if "of" in field_def and original_type == "array":
#             of_content_list = []
#             for item in field_def.get("of", []):
#                 if item.get("type") == "object" and "fields" in item:
#                     inline_fields = "".join([format_field(f, indent_level + 2) for f in item.get("fields", [])])
#                     of_content_list.append(f"{indent}  {{\n{indent}    type: 'object',\n{indent}    fields: [\n{inline_fields}{indent}    ]\n{indent}  }}")
#                 else:
#                     of_content_list.append(f"{indent}  {json.dumps(item)}")
#             ts_parts.append(f"of: [\n{','.join(of_content_list)}\n{indent}]")
        
#         if "to" in field_def: ts_parts.append(f"to: {json.dumps(field_def['to'])}")
#         if "options" in field_def: ts_parts.append(f"options: {json.dumps(field_def['options'])}")

#         return f"{indent}defineField({{\n{indent}  " + f",\n{indent}  ".join(ts_parts) + f"\n{indent}}}),\n"

#     field_ts_strings = "".join([format_field(field) for field in schema_def.get("fields", [])])
#     schema_type = 'document' if schema_def.get('type') == 'document' else 'object'
#     return f"""import {{defineType, defineField, type Rule}} from 'sanity'

# export default defineType({{
#   name: '{schema_def.get('name', 'unnamed')}',
#   title: '{schema_def.get('title', 'Unnamed')}',
#   type: '{schema_type}',
#   fields: [
# {field_ts_strings}
#   ],
#   {f"preview: {{ select: {{ title: 'title' }} }}," if schema_def.get('type') == 'document' else ''}
# }})
# """

# def generate_all_files(all_schemas: List[dict], plan: dict):
#     logging.info("\n--- 💾 PHASE 4: Generating All Project Files ---")
#     if os.path.exists(SCHEMAS_DIR):
#         shutil.rmtree(SCHEMAS_DIR)
#         logging.info(f"Removed existing directory: {SCHEMAS_DIR}")

#     for folder in ["documents", "objects", "plugins/i18n"]:
#         os.makedirs(os.path.join(SCHEMAS_DIR, folder), exist_ok=True)
    
#     i18n_schema_names = []
    
#     # --- THIS IS THE CORRECTED TEMPLATE ---
#     # All literal curly braces are now doubled (e.g., {{ and }})
#     i18n_type_template = """import {{defineType}} from 'sanity'

# export default defineType({{
#   name: 'internationalizedArray{type_pascal}',
#   type: 'array',
#   title: 'Internationalized {type_pascal}',
#   of: [{{ type: '{type_camel}' }}],
#   options: {{
#     layout: 'tabs',
#   }},
# }})"""

#     for t in ["String", "Text", "Image", "File", "Url", "Slug"]:
#         file_path = os.path.join(SCHEMAS_DIR, "plugins/i18n", f"{t.lower()}.ts")
#         # The .format() call itself remains the same
#         file_content = i18n_type_template.format(type_pascal=t, type_camel=t.lower())
#         with open(file_path, "w", encoding="utf-8") as f: f.write(file_content.strip())
#         i18n_schema_names.append(f"internationalizedArray{t}")
        
#     logging.info(f"   ✅ Wrote {len(i18n_schema_names)} I18N Helper Schemas (with Tabs UI)")

#     schemas_by_name = {s['name']: s for s in all_schemas if isinstance(s, dict) and 'name' in s}
#     user_schema_names = []
#     for schema_name, schema_data in schemas_by_name.items():
#         if not isinstance(schema_data, dict):
#             logging.error(f"Skipping generation for '{schema_name}' as it is not a valid schema dictionary.")
#             continue
#         folder = "objects"
#         if schema_data.get("type") == "document": folder = "documents"
#         file_path = os.path.join(SCHEMAS_DIR, folder, f"{to_kebab_case(schema_name)}.ts")
#         try:
#             with open(file_path, "w", encoding="utf-8") as f: f.write(generate_ts_code(schema_data))
#             logging.info(f"   ✅ Wrote {folder.upper()}: {folder}/{to_kebab_case(schema_name)}.ts")
#             user_schema_names.append(schema_name)
#         except Exception as e:
#             logging.error(f"   ❌ FAILED to write {file_path}. Reason: {e}")

#     all_schema_names = sorted(user_schema_names + i18n_schema_names)
#     imports = []
#     for name in sorted(user_schema_names):
#         schema_info = schemas_by_name.get(name)
#         if not schema_info: continue
#         folder = "objects" if schema_info.get("type") != "document" else "documents"
#         imports.append(f"import {name} from './{folder}/{to_kebab_case(name)}'")
#     for name in sorted(i18n_schema_names):
#         type_name = name.replace("internationalizedArray", "").lower()
#         imports.append(f"import {name} from './plugins/i18n/{type_name}'")

#     with open(os.path.join(SCHEMAS_DIR, "index.ts"), "w", encoding="utf-8") as f:
#         f.write(f"// This file is auto-generated by the AI Schema Architect.\n{chr(10).join(imports)}\n\nexport const schemaTypes = [\n  {', '.join(all_schema_names)}\n];\n")
#     logging.info(f"   ✅ Wrote main schema index file: {SCHEMAS_DIR}/index.ts")

# # --- 🚀 6. MAIN EXECUTION FLOW ---
# def main():
#     logging.info("🚀 AI Schema Architect (v19 - Resilient Architect) 🚀")
#     if not all([FIGMA_API_KEY, FIGMA_FILE_KEY, GEMINI_API_KEY]):
#         logging.critical("❌ CONFIGURATION ERROR: Missing required API keys in .env file.")
#         sys.exit(1)

#     genai.configure(api_key=GEMINI_API_KEY)
#     ai_model = genai.GenerativeModel(GEMINI_MODEL_NAME)

#     classified_sections = classify_figma_sections()
#     if not classified_sections or not classified_sections.get("page_sections"):
#         logging.critical("❌ No page sections found in Figma. Cannot proceed. Check FIGMA_MAIN_FRAME_NAME.")
#         return

#     all_figma_components = classified_sections['header'] + classified_sections['footer'] + classified_sections['page_sections']
#     plan = phase_one_architect_plan(all_figma_components, ai_model)
#     if not plan:
#         logging.critical("❌ Failed to generate architectural plan in Phase 1. Exiting.")
#         return

#     all_schema_data = []
    
#     all_planned_schemas = [
#         {'name': name, 'type': 'document'} for name in plan.get('documents', [])
#     ] + [
#         {'name': name, 'type': 'object'} for name in plan.get('objects', [])
#     ]

#     for schema_info in all_planned_schemas:
#         name = schema_info['name']
#         classification = schema_info['type']
#         nodes_to_analyze = []

#         if name == 'siteSettings':
#             nodes_to_analyze.extend(classified_sections.get('header', []))
#             nodes_to_analyze.extend(classified_sections.get('footer', []))
#             if not nodes_to_analyze:
#                 logging.warning(f"⚠️ `siteSettings` is in the plan, but no Header/Footer frames found in Figma. It will be a minimal schema.")
#         else:
#             exact_matches = [s for s in all_figma_components if to_camel_case(s['name']) == name]
#             if exact_matches:
#                 nodes_to_analyze = exact_matches
#             elif classification == 'document':
#                 singular_name_pascal = to_pascal_case(name)
#                 heuristic_matches = [s for s in all_figma_components if singular_name_pascal in to_pascal_case(s['name'])]
#                 if heuristic_matches:
#                     nodes_to_analyze = heuristic_matches
        
#         # Pass only the *most relevant* nodes to the next phase to avoid ambiguity.
#         # This is a key part of the bug fix, preventing the AI from getting confused by multiple inputs.
#         schema_data = phase_two_generate_field_data(name, classification, plan, nodes_to_analyze, ai_model)
        
#         if schema_data:
#             all_schema_data.append(schema_data)

#     if not all_schema_data:
#         logging.critical("❌ No schemas were generated in Phase 2. Exiting.")
#         return

#     correct_and_validate_schemas(all_schema_data, plan)
    
#     generate_all_files(all_schema_data, plan)

#     logging.info("\n✨ All Done! ✨")
#     print("\n--- NEXT STEPS ---")
#     print(f"1. A new directory '{SCHEMAS_DIR}' has been created with a **production-ready schema**, including validation rules, based on a deep architectural analysis.")
#     print("2. **CRITICAL:** Install the required Sanity plugin:")
#     print("   `npm install sanity-plugin-internationalized-array` (or pnpm/yarn)")
#     print("\n3. **CRITICAL: In `sanity.config.ts`**, configure the plugin. This is required for it to work!")
#     print("   // In your plugins array, add:")
#     print("   internationalizedArray({")
#     print("     languages: [{id: 'en', title: 'English'}, {id: 'es', title: 'Spanish'}], // Customize your languages")
#     print("     defaultLanguage: 'en',")
#     print("     fieldTypes: ['string', 'text', 'image', 'file', 'url', 'slug'],")
#     print("   })")
#     print(f"\n4. Copy the entire generated `{SCHEMAS_DIR}` directory into your Sanity project.")
#     print("5. In `sanity.config.ts`, import `schemaTypes` and set `schema: { types: schemaTypes }`.")
#     print("6. Start Sanity Studio to see your precise, architecturally-sound, multi-language schema!")

# if __name__ == "__main__":
#     try:
#         import inflection
#     except ImportError:
#         print("\nERROR: Required library `inflection` not found. Please run: pip install inflection\n")
#         sys.exit(1)
#     main()





































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
FIGMA_API_KEY = os.getenv(
    "FIGMA_API_KEY"
)
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
    # --- MODIFIED: Heavily enhanced prompt for better reusability and architecture. ---
    prompt = f"""
You are a top-tier Sanity.io Lead Architect. Your goal is to create a highly reusable, scalable, and DRY schema plan by analyzing a Figma design's JSON structure.

**Architectural Rules (Follow in order):**

1.  **Core Philosophy: `document` vs. `object` (MOST IMPORTANT RULE):**
    *   **`document`:** For core, reusable business "entities." Ask: "Would an editor manage this content independently of a page?" Examples: `post`, `author`, `product`, `teamMember`, `testimonial`, `service`, `caseStudy`. A `header` and `footer` are also managed this way.
    *   **`object`:** For structural components used to build pages. They have no meaning on their own. Examples: `heroSection`, `featureList`, `logoCloud`, `statItem`. These are the building blocks.

2.  **The Sub-Component Rule (For Maximum Reusability):**
    *   **CRITICAL:** Scan the *internal structure* (`children` arrays) of all provided page sections.
    *   If you see small, repeated components (e.g., nodes named 'Button', 'CTA', 'Link', 'Navigation Item'), you **MUST** define a separate, reusable `object` for them.
    *   **Examples of sub-components to create:** `ctaButton`, `navLink`, `socialLink`, `formField`. This is key to a DRY schema. Instead of defining button fields inside `heroSection` and `ctaSection`, you define `ctaButton` once and reference it.

3.  **The Grid Rule (Identifying `document` types):**
    *   When a section contains a repeating list of complex items (e.g., a "Team" section with multiple "Team Member" children), this signals a `document`/`object` pair.
    *   The repeating item (`teamMember`) becomes a `document`.
    *   The container section (`teamSection`) becomes an `object` that holds an array of `references` to `teamMember` documents.

4.  **Global Content Rule (Header, Footer, Settings):**
    *   If you infer a 'Header' or 'Footer' from the section names, you **MUST** create `header` and `footer` as **`document`** types.
    *   You **MUST** also create a `siteSettings` document. This document will contain fields that `reference` the new `header` and `footer` documents. Do NOT create `headerSettings` or `footerSettings` as separate schemas. The content lives in the `header` and `footer` documents.

5.  **CRITICAL NAMING:** All schema names in your output MUST be in EXACT camelCase format (e.g., "metricsSection", "teamMember", "ctaButton").

6.  **Always include a `page` document.** This is the primary document that will use the `object` schemas in its page builder.

**Figma JSON Structure to Analyze:**
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
    # --- MODIFIED: Update exclusion list to match new architecture
    page_builder_objects = [
        obj for obj in all_objects if obj not in ["siteSettings", "header", "footer"]
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
    # --- MODIFIED: Updated instructions for siteSettings to match new architecture ---
    elif schema_name == "siteSettings":
        special_instructions = "**SPECIAL INSTRUCTION FOR 'siteSettings':** This document must contain a `header` field of type `reference` to the `header` document, and a `footer` field of type `reference` to the `footer` document. Do not define header/footer content here, only the references."
    elif schema_name == "header":
        special_instructions = "**SPECIAL INSTRUCTION FOR 'header':** This document defines the site-wide header. It should contain fields for logo and an array of navigation items (e.g., using a `navLink` object if one was planned)."
    elif schema_name == "footer":
        special_instructions = "**SPECIAL INSTRUCTION FOR 'footer':** This document defines the site-wide footer. It should contain fields for copyright text, and arrays for things like social media links or footer navigation (e.g., using a `navLink` or `socialLink` object if planned)."

    prompt = f"""
You are an expert Sanity.io schema generator. Your most important task is to create CONCISE and FOCUSED TypeScript schema code. 

### **CRITICAL: MINIMAL FIELD APPROACH**
- **Create ONLY essential content fields** - avoid over-engineering
- **Focus on actual content**, not visual styling or layout elements  
- **Maximum 3-5 fields per schema** unless absolutely necessary
- **Combine related fields** rather than creating separate ones for each visual element
- **For schemas like 'heroSection', if a `ctaButton` object exists, the hero should have a field of type `ctaButton`, NOT separate fields for button text and URL.**

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
- **Correct:** `of: [{{type: 'navLink'}}]`
- **INCORRECT:** `of: [{{'navLink'}}]`

### **Rule 3c: Multiple Items of Same Type in Arrays - Use Unique Names (CRITICAL)**
When an array contains multiple items of the same type, each must have a unique `name`:
- **Correct:** 
of: [
{{type: 'reference', name: 'primaryReference', to: [{{type: 'page'}}]}},
{{type: 'reference', name: 'secondaryReference', to: [{{type: 'post'}}]}}
]

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

### **Rule 8: Essential Fields Only**
**For ANY schema, include ONLY these types of fields:**
1. **Core Content**: Title, description, main text
2. **Media**: Primary image or icon (if essential)
3. **Actions**: A field referencing a reusable `ctaButton` object (if one exists), or a link.
4. **References**: Links to other documents (e.g., an array of `references` to `teamMember`).

**DO NOT CREATE FIELDS FOR:**
- Visual styling (colors, spacing, layout)
- Multiple variations of the same content type
- Decorative elements
- Container or wrapper elements
- Every single visual element you see

### **Field Naming Convention:**
- Use simple, clear names: `title`, `description`, `image`, `button`, `links`
- Avoid verbose names like `primaryHeaderTitle`, `mainContentDescription`

---
**Your Task:**
Generate a MINIMAL, focused TypeScript schema for **`{schema_name}`** with ONLY essential content fields.

**Figma Structure to Analyze:**
```json
{structure_info}
{special_instructions}
Focus on CONTENT and REUSABILITY. Keep it simple and essential.
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


def correct_generated_code(code: str, all_valid_names: Set[str]) -> str:
    """
    Applies a series of corrections to the AI-generated code to fix common, predictable errors.
    """
    original_code = code
    corrections_applied = []
    if code.startswith("```") or code.endswith("```"):
        code = re.sub(
            r"^```(?:typescript|javascript|ts|js)?\s*", "", code, flags=re.MULTILINE
        )
        code = re.sub(r"\s*```\s*$", "", code, flags=re.MULTILINE)
        corrections_applied.append("removed markdown formatting")

    if re.search(r";```\w*", code):
        code = re.sub(r";```\w*\s*", "", code)
        corrections_applied.append("removed stray markdown syntax")

    validation_pattern = r"\(Rule:\s*[A-Za-z_][A-Za-z0-9_]*\)"
    if re.search(validation_pattern, code):
        code = re.sub(validation_pattern, r"(Rule)", code)
        corrections_applied.append("validation function syntax (Rule: Rule) → (Rule)")

    defineType_in_array_pattern = r"of:\s*\[\s*defineType\s*\(\s*\{"
    if re.search(defineType_in_array_pattern, code):
        code = re.sub(r"of:\s*\[\s*defineType\s*\(\s*\{", "of: [{", code)
        code = re.sub(r"\}\s*\)\s*,?\s*\]", "}]", code)
        corrections_applied.append("defineType inside arrays → plain objects")

    missing_type_pattern = r"of:\s*\[\s*\{\s*['\"]([^'\"]+)['\"]\s*\}\s*\]"
    if re.search(missing_type_pattern, code):
        code = re.sub(missing_type_pattern, r"of: [{type: '\1'}]", code)
        corrections_applied.append("added missing 'type:' property in array items")

    i18n_image_fields_pattern = r"(type:\s*['\"]internationalizedArray(Image|File)['\"][^}]*?),\s*fields:\s*\[[^\]]*?\]"
    if re.search(i18n_image_fields_pattern, code, re.DOTALL):
        code = re.sub(i18n_image_fields_pattern, r"\1", code, flags=re.DOTALL)
        corrections_applied.append("removed 'fields' from internationalizedArray type")

    i18n_array_of_pattern = r"(type:\s*['\"]internationalizedArray(?:Text|String|Url|Slug)['\"][^}]*?),\s*of:\s*\[[^\]]*?\]"
    if re.search(i18n_array_of_pattern, code, re.DOTALL):
        code = re.sub(i18n_array_of_pattern, r"\1", code, flags=re.DOTALL)
        corrections_applied.append("removed 'of' from internationalizedArray type")

    name_map = {name.lower(): name for name in all_valid_names}
    type_corrections = []

    def replace_type_reference(match):
        quote_char = match.group(1)
        type_name = match.group(2)
        built_in_types = {
            "string", "text", "image", "file", "url", "slug", "number",
            "boolean", "array", "object", "reference", "block", "date", "datetime",
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

    if "defineType" not in code and "defineField" not in code:
        if "name:" in code and "title:" in code and "type:" in code:
            code = f"import {{defineType, defineField}} from 'sanity'\n\n{code}"
            corrections_applied.append("added missing defineType/defineField import")

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

    if corrections_applied:
        logging.info(
            f"    🔧 Auto-corrections applied to '{os.path.basename(code[:30])}...': {' | '.join(corrections_applied)}"
        )

    return code


def generate_all_files(all_schemas: List[dict], plan: dict):
    logging.info("\n--- 💾 PHASE 4: Generating All Project Files ---")
    if os.path.exists(SCHEMAS_DIR):
        shutil.rmtree(SCHEMAS_DIR)
    for folder in ["documents", "objects"]:
        os.makedirs(os.path.join(SCHEMAS_DIR, folder), exist_ok=True)
    all_schema_names = []
    for schema_data in all_schemas:
        schema_name = schema_data["name"]
        folder = "documents" if schema_data["type"] == "document" else "objects"
        file_name = f"{to_kebab_case(schema_name)}.ts"
        file_path = os.path.join(SCHEMAS_DIR, folder, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(schema_data["code"])
        logging.info(f"   ✅ Wrote {folder.upper()[:-1]} SCHEMA: {folder}/{file_name}")
        all_schema_names.append(schema_name)

    all_final_names = sorted(all_schema_names)
    imports = []
    for name in sorted(all_schema_names):
        schema_info = next((s for s in all_schemas if s["name"] == name), None)
        if schema_info:
            folder = "documents" if schema_info["type"] == "document" else "objects"
            imports.append(f"import {name} from './{folder}/{to_kebab_case(name)}'")

    index_content = f"// This file is auto-generated by the AI Schema Architect.\n{chr(10).join(imports)}\n\nexport const schemaTypes = [\n  {',\n  '.join(all_final_names)},\n];\n"
    with open(os.path.join(SCHEMAS_DIR, "index.ts"), "w", encoding="utf-8") as f:
        f.write(index_content)
    logging.info(f"   ✅ Wrote main schema index file: {SCHEMAS_DIR}/index.ts")


# --- 🚀 6. MAIN EXECUTION FLOW ---


def main():
    setup_logging()
    logging.info("🚀 AI Schema Architect (v3 - Enhanced Reusability) Initializing... 🚀")
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

    all_valid_names = set(plan.get("documents", [])) | set(plan.get("objects", []))
    logging.info(
        f"📋 Plan created. Documents: {plan.get('documents', [])}. Objects: {plan.get('objects', [])}"
    )

    all_schema_data = []
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

    logging.info("\n🔍 PHASE 3: Correcting all generated code...")
    corrected_schemas = []
    for schema in all_schema_data:
        logging.info(f"  -> Correcting {schema['name']}...")
        corrected_code = correct_generated_code(schema["code"], all_valid_names)
        corrected_schemas.append({**schema, "code": corrected_code})
    logging.info("✅ PHASE 3: Code correction complete.")

    generate_all_files(corrected_schemas, plan)

    logging.info("\n✨ All Done! High-Quality, Reusable Schemas Generated! ✨")
    print("\n--- NEXT STEPS ---")
    print(
        f"1. A new directory '{SCHEMAS_DIR}' has been created with a professional, reusable schema structure."
    )
    print(
        "2. The AI has identified sub-components like buttons for reusability and correctly structured Header/Footer as documents."
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
    print("            {id: 'es', title: 'Spanish'}, // Add your languages")
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
        "\n✅ You will now find `Header` and `Footer` as manageable documents in the Studio, and objects like `ctaButton` are reused across page sections."
    )


if __name__ == "__main__":
    main()