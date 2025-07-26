import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'quotesection',
  title: 'Quote Section',
  type: 'object',
  fields: [
    defineField({
      name: 'quote',
      title: 'Quote Text',
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
      name: 'authorImage',
      title: 'Author Image',
      type: 'internationalizedArrayImage',
    }),
  ],
  preview: {
    select: {
      title: 'quote.0.value',
      subtitle: 'author.0.value',
      media: 'authorImage.0.value.asset',
    },
    prepare({title, subtitle, media}) {
      return {
        title: title || 'Untitled Quote Section',
        subtitle: subtitle ? `by ${subtitle}` : 'No author specified',
        media: media,
      }
    },
  },
})