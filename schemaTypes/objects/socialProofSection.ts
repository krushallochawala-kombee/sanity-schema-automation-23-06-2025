import {defineType, defineField} from 'sanity'

const SUPPORTED_LOCALES = [
  {id: 'en', title: 'English'},
  {id: 'es', title: 'Spanish'},
]
const DEFAULT_LOCALE = 'en'

export default defineType({
  name: 'socialProofSection',
  title: 'Social Proof Section',
  type: 'object',
  fields: [
    defineField({
      name: 'preHeading',
      title: 'Pre-heading Text',
      type: 'internationalizedArrayString',
    }),
    defineField({
      name: 'companyLogos',
      title: 'Company Logos',
      type: 'array',
      of: [
        defineField({
          name: 'companyLogoEntry',
          title: 'Company Logo Entry',
          type: 'object',
          fields: [
            defineField({
              name: 'logoImage',
              title: 'Logo Image',
              type: 'image',
              description: "The visual logo of the company (e.g., 'Layers', 'Sisyphus').",
              options: {hotspot: true},
              validation: (Rule) => Rule.required().error('A logo image is required.'),
            }),
            defineField({
              name: 'companyName',
              title: 'Company Name',
              type: 'internationalizedArrayString',
              description:
                'The full name of the company, used for alt text and potentially for display if the logo is an icon.',
              validation: (Rule) =>
                Rule.required().error('Company name is required for accessibility.'),
            }),
            defineField({
              name: 'companyWebsite',
              title: 'Company Website URL',
              type: 'url',
              description: "Optional: URL to the company's official website.",
            }),
          ],
          preview: {
            select: {
              title: 'companyName.0.value',
              media: 'logoImage',
            },
          },
        }),
      ],
    }),
  ],
})
