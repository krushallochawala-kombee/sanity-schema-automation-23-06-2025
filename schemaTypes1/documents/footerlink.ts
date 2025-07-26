import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'footerlink',
  title: 'Footer Link',
  type: 'document',
  fields: [
    defineField({
      name: 'title',
      title: 'Link Text',
      type: 'internationalizedArrayString',
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'url',
      title: 'URL',
      type: 'internationalizedArrayUrl',
      validation: (Rule) => Rule.required(),
    }),
  ],
  preview: {
    select: {
      title: 'title.0.value',
      subtitle: 'url.0.value',
    },
    prepare({title, subtitle}) {
      return {
        title: title || 'Untitled Footer Link',
        subtitle: subtitle,
      }
    },
  },
})