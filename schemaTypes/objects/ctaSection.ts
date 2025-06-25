import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'ctaSection',
  title: 'Call to Action Section',
  type: 'object',
  fields: [
    defineField({
      name: 'heading',
      title: 'Heading',
      type: 'internationalizedArrayString',
    }),
    defineField({
      name: 'description',
      title: 'Description',
      type: 'internationalizedArrayText',
    }),
    defineField({
      name: 'primaryButton',
      title: 'Primary Button',
      type: 'object',
      fields: [
        defineField({name: 'text', type: 'internationalizedArrayString', title: 'Text'}),
        defineField({name: 'url', type: 'url', title: 'URL'}),
      ],
    }),
    defineField({
      name: 'secondaryButton',
      title: 'Secondary Button',
      type: 'object',
      fields: [
        defineField({name: 'text', type: 'internationalizedArrayString', title: 'Text'}),
        defineField({name: 'url', type: 'url', title: 'URL'}),
      ],
    }),
  ],
})
