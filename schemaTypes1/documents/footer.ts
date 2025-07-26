import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'footer',
  title: 'Footer',
  type: 'document',
  fields: [
    defineField({
      name: 'logo',
      title: 'Company Logo',
      type: 'reference',
      to: [{type: 'companylogo'}],
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'columns',
      title: 'Footer Link Columns',
      type: 'array',
      of: [
        {
          type: 'reference',
          to: [{type: 'footerlinkcolumn'}],
        },
      ],
      description: 'Add and order the columns of links displayed in the footer.',
      validation: (Rule) => Rule.required().min(1),
    }),
    defineField({
      name: 'copyright',
      title: 'Copyright Text',
      type: 'internationalizedArrayString',
      description: 'The copyright information displayed at the bottom of the footer.',
      validation: (Rule) => Rule.required(),
    }),
  ],
  preview: {
    select: {
      copyright: 'copyright.0.value',
      columnCount: 'columns.length',
    },
    prepare({copyright, columnCount}) {
      return {
        title: 'Footer',
        subtitle: `${columnCount || 0} columns | Copyright: ${copyright || 'N/A'}`,
      }
    },
  },
})
