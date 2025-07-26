import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'socialproofsection',
  title: 'Social Proof Section',
  type: 'object',
  fields: [
    defineField({
      name: 'title',
      title: 'Section Title',
      type: 'internationalizedArrayString',
      description: 'Main heading for the social proof section.',
    }),
    defineField({
      name: 'testimonials',
      title: 'Testimonials',
      type: 'array',
      description: 'List of testimonials or quotes.',
      of: [
        {
          name: 'testimonialItem',
          title: 'Testimonial Item',
          type: 'object',
          fields: [
            defineField({
              name: 'quote',
              title: 'Quote',
              type: 'internationalizedArrayText',
              validation: (Rule) => Rule.required(),
            }),
            defineField({
              name: 'author',
              title: 'Author',
              type: 'internationalizedArrayString',
              validation: (Rule) => Rule.required(),
            }),
            defineField({
              name: 'role',
              title: 'Role/Company',
              type: 'internationalizedArrayString',
              description: 'e.g., "CEO of Acme Corp"',
            }),
            defineField({
              name: 'image',
              title: 'Author Image',
              type: 'internationalizedArrayImage',
            }),
          ],
          preview: {
            select: {
              title: 'author.0.value',
              subtitle: 'quote.0.value',
              media: 'image.0.value.asset',
            },
            prepare({title, subtitle, media}) {
              return {
                title: title || 'Untitled Testimonial',
                subtitle: subtitle ? `${subtitle.substring(0, 50)}...` : '',
                media: media,
              }
            },
          },
        },
      ],
    }),
  ],
  preview: {
    select: {
      title: 'title.0.value',
    },
    prepare({title}) {
      return {
        title: title || 'Social Proof Section',
        subtitle: 'Social Proof Section',
      }
    },
  },
})