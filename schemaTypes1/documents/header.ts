import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'header',
  title: 'Header',
  type: 'document',
  fields: [
    defineField({
      name: 'logo',
      title: 'Company Logo',
      description: 'Select the logo to display in the header.',
      type: 'reference',
      to: [{type: 'companylogo'}],
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'navigation',
      title: 'Navigation Items',
      description: 'Define the main navigation links.',
      type: 'array',
      of: [
        {
          name: 'navigationItem',
          title: 'Navigation Item',
          type: 'object',
          fields: [
            defineField({
              name: 'label',
              title: 'Label',
              type: 'internationalizedArrayString',
              validation: (Rule) => Rule.required(),
            }),
            defineField({
              name: 'link',
              title: 'Link',
              description: 'Select an internal page or provide an external URL.',
              type: 'array',
              validation: (Rule) => Rule.max(1).required(),
              of: [
                {
                  type: 'object',
                  name: 'externalLink',
                  title: 'External URL',
                  fields: [
                    defineField({
                      name: 'url',
                      title: 'URL',
                      type: 'url',
                      validation: (Rule) => Rule.required(),
                    }),
                  ],
                },
                {
                  type: 'reference',
                  name: 'internalPage',
                  title: 'Internal Page',
                  to: [{type: 'page'}],
                },
              ],
            }),
          ],
          preview: {
            select: {
              title: 'label.0.value',
              subtitle: 'link.0._type',
            },
            prepare({title, subtitle}) {
              const linkType = subtitle === 'url' ? 'External' : 'Internal Page'
              return {
                title: title || 'Untitled Navigation Item',
                subtitle: `Link Type: ${linkType}`,
              }
            },
          },
        },
      ],
    }),
    defineField({
      name: 'ctaButton',
      title: 'Call to Action Button',
      description: 'An optional CTA button in the header.',
      type: 'object',
      fields: [
        defineField({
          name: 'label',
          title: 'Label',
          type: 'internationalizedArrayString',
          validation: (Rule) => Rule.required(),
        }),
        defineField({
          name: 'link',
          title: 'Link',
          description: 'Select an internal page or provide an external URL for the CTA button.',
          type: 'array',
          validation: (Rule) => Rule.max(1).required(),
          of: [
            {
              type: 'object',
              name: 'externalCtaLink',
              title: 'External URL',
              fields: [
                defineField({
                  name: 'url',
                  title: 'URL',
                  type: 'url',
                  validation: (Rule) => Rule.required(),
                }),
              ],
            },
            {
              type: 'reference',
              name: 'internalCtaPage',
              title: 'Internal Page',
              to: [{type: 'page'}],
            },
          ],
        }),
      ],
      // No preview needed for the object itself, as it's part of the header document.
    }),
  ],
  preview: {
    prepare() {
      return {
        title: 'Main Header Settings',
        subtitle: 'Global header configuration',
      }
    },
  },
})
