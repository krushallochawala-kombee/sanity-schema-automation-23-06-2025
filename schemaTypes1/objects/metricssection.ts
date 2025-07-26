import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'metricssection',
  title: 'Metrics Section',
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
      name: 'metrics',
      title: 'Metrics',
      type: 'array',
      of: [{type: 'reference', to: [{type: 'metricitem'}]}],
      validation: (Rule) => Rule.min(1).error('A metrics section must have at least one metric.'),
    }),
  ],
  preview: {
    select: {
      title: 'title.0.value',
      subtitle: 'metrics.length',
    },
    prepare({title, subtitle}) {
      return {
        title: title || 'Untitled Metrics Section',
        subtitle: subtitle ? `${subtitle} metrics` : 'No metrics',
      }
    },
  },
})