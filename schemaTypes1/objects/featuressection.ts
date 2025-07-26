import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'featuressection',
  title: 'Features Section',
  type: 'object',
  fields: [
    defineField({
      name: 'title',
      title: 'Section Title',
      type: 'internationalizedArrayString',
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'description',
      title: 'Description',
      type: 'internationalizedArrayText',
    }),
    defineField({
      name: 'features',
      title: 'Features',
      type: 'array',
      of: [
        {
          type: 'reference',
          to: [{type: 'featureitem'}],
        },
      ],
      validation: (Rule) => Rule.required().min(1),
    }),
  ],
  preview: {
    select: {
      title: 'title.0.value',
      subtitle: 'description.0.value',
    },
    prepare({title, subtitle}) {
      return {
        title: title || 'Features Section',
        subtitle: subtitle,
      }
    },
  },
})