import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'quoteSection',
  title: 'Quote Section',
  type: 'object',
  fields: [
    defineField({
      name: 'companyLogo',
      title: 'Company Logo',
      type: 'image',
      options: {hotspot: true},
    }),
    defineField({
      name: 'companyName',
      title: 'Company Name',
      type: 'internationalizedArrayString',
    }),
    defineField({
      name: 'quoteText',
      title: 'Quote Text',
      type: 'internationalizedArrayText',
    }),
    defineField({
      name: 'authorAvatar',
      title: 'Author Avatar',
      type: 'image',
      options: {hotspot: true},
    }),
    defineField({
      name: 'authorName',
      title: 'Author Name',
      type: 'internationalizedArrayString',
    }),
    defineField({
      name: 'authorRole',
      title: 'Author Role',
      type: 'internationalizedArrayString',
    }),
  ],
})
