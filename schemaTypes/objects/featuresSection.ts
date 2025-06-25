import {defineType, defineField} from 'sanity'

const SUPPORTED_LOCALES = [
  {id: 'en', title: 'English'},
  {id: 'es', title: 'Spanish'},
]
const DEFAULT_LOCALE = 'en'

export default defineType({
  name: 'featuresSection',
  title: 'Features Section',
  type: 'object',
  fields: [
    defineField({
      name: 'topLabel',
      title: 'Top Label',
      type: 'internationalizedArrayString',
    }),
    defineField({
      name: 'heading',
      title: 'Heading',
      type: 'internationalizedArrayString',
    }),
    defineField({
      name: 'subheading',
      title: 'Subheading',
      type: 'internationalizedArrayText',
    }),
    defineField({
      name: 'features',
      title: 'Feature Items',
      type: 'array',
      of: [
        defineField({
          name: 'featureItem',
          title: 'Feature Item',
          type: 'object',
          fields: [
            defineField({
              name: 'icon',
              title: 'Icon',
              type: 'image',
              description: 'An icon representing this feature.',
              options: {hotspot: true},
            }),
            defineField({
              name: 'title',
              title: 'Title',
              type: 'internationalizedArrayString',
              description: 'The title of the feature item.',
            }),
            defineField({
              name: 'description',
              title: 'Description',
              type: 'internationalizedArrayText',
              description: 'A detailed description of the feature item.',
            }),
          ],
          preview: {
            select: {
              title: 'title.0.value',
              subtitle: 'description.0.value',
              media: 'icon',
            },
          },
        }),
      ],
    }),
  ],
})
