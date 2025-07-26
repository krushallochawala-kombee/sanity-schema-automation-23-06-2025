import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'herosection',
  title: 'Hero Section',
  type: 'object',
  fields: [
    defineField({
      name: 'title',
      title: 'Title',
      type: 'internationalizedArrayString',
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'description',
      title: 'Description',
      type: 'internationalizedArrayText',
    }),
    defineField({
      name: 'image',
      title: 'Image',
      type: 'internationalizedArrayImage',
    }),
    defineField({
      name: 'ctaButton',
      title: 'Call to Action Button',
      type: 'object',
      fields: [
        defineField({
          name: 'text',
          title: 'Button Text',
          type: 'internationalizedArrayString',
          validation: (Rule) => Rule.required(),
        }),
        defineField({
          name: 'link',
          title: 'Button Link',
          type: 'internationalizedArrayUrl',
          validation: (Rule) => Rule.required(),
        }),
      ],
    }),
  ],
  preview: {
    select: {
      title: 'title.0.value',
      subtitle: 'description.0.value',
      media: 'image.0.value.asset',
    },
    prepare({title, subtitle, media}) {
      return {
        title: title || 'Untitled Hero Section',
        subtitle: subtitle,
        media: media,
      }
    },
  },
})