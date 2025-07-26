import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'footerlinkcolumn',
  title: 'Footer Link Column',
  type: 'document',
  fields: [
    defineField({
      name: 'title',
      title: 'Column Title',
      type: 'internationalizedArrayString',
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'links',
      title: 'Links',
      type: 'array',
      of: [
        {
          type: 'reference',
          to: [{type: 'footerlink'}],
        },
      ],
      validation: (Rule) => Rule.required().min(1),
    }),
  ],
  preview: {
    select: {
      title: 'title.0.value',
      linkCount: 'links.length',
    },
    prepare({title, linkCount}) {
      return {
        title: title || 'Untitled Column',
        subtitle: linkCount ? `${linkCount} link${linkCount === 1 ? '' : 's'}` : 'No links',
      }
    },
  },
})
