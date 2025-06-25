import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'footer',
  title: 'Footer Section',
  type: 'object',
  fields: [
    defineField({
      name: 'navigationColumns',
      title: 'Navigation Columns',
      type: 'array',
      of: [
        defineField({
          name: 'footerColumn',
          title: 'Footer Column',
          type: 'object',
          fields: [
            defineField({
              name: 'columnTitle',
              title: 'Column Title',
              type: 'internationalizedArrayString',
            }),
            defineField({
              name: 'links',
              title: 'Links',
              type: 'array',
              of: [
                defineField({
                  name: 'footerLink',
                  title: 'Footer Link',
                  type: 'object',
                  fields: [
                    defineField({
                      name: 'labelText',
                      title: 'Label Text',
                      type: 'internationalizedArrayString',
                    }),
                    defineField({
                      name: 'url',
                      title: 'URL',
                      type: 'url',
                      validation: (Rule) =>
                        Rule.uri({
                          scheme: ['http', 'https', 'mailto', 'tel'],
                        }),
                    }),
                    defineField({
                      name: 'badgeText',
                      title: 'Badge Text',
                      type: 'internationalizedArrayString',
                      description:
                        "Optional text to display as a badge next to the link (e.g., 'New').",
                    }),
                  ],
                  preview: {
                    select: {
                      title: 'labelText.0.value',
                      subtitle: 'url',
                      badge: 'badgeText.0.value',
                    },
                    prepare({title, subtitle, badge}) {
                      return {
                        title: title,
                        subtitle: subtitle + (badge ? ` (${badge})` : ''),
                      }
                    },
                  },
                }),
              ],
            }),
          ],
          preview: {
            select: {
              title: 'columnTitle.0.value',
            },
          },
        }),
      ],
    }),
    defineField({
      name: 'bottomSection',
      title: 'Bottom Section',
      type: 'object',
      fields: [
        defineField({
          name: 'copyright',
          title: 'Copyright Text',
          type: 'internationalizedArrayString',
        }),
        defineField({
          name: 'socialLinks',
          title: 'Social Media Links',
          type: 'array',
          of: [
            defineField({
              name: 'socialLink',
              type: 'object',
              title: 'Social Link',
              fields: [
                defineField({name: 'icon', type: 'image', title: 'Icon'}),
                defineField({name: 'url', type: 'url', title: 'URL'}),
              ],
            }),
          ],
        }),
      ],
    }),
  ],
})
