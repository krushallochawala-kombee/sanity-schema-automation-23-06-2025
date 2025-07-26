import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'companylogo',
  title: 'Company Logo',
  type: 'document',
  fields: [
    defineField({
      name: 'image',
      title: 'Logo Image',
      type: 'internationalizedArrayImage',
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'altText',
      title: 'Alt Text',
      description: 'Important for accessibility and SEO.',
      type: 'internationalizedArrayString',
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'link',
      title: 'Link URL',
      description: 'Optional URL the logo links to.',
      type: 'internationalizedArrayUrl',
    }),
  ],
  preview: {
    select: {
      title: 'altText.0.value',
      media: 'image.0.value.asset',
    },
    prepare({title, media}) {
      return {
        title: title || 'Untitled Logo',
        media: media,
      }
    },
  },
})