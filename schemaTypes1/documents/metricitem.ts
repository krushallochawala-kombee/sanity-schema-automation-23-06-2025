import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'metricitem',
  title: 'Metric Item',
  type: 'document',
  fields: [
    defineField({
      name: 'value',
      title: 'Metric Value',
      type: 'internationalizedArrayString',
      description: 'e.g., "10K+", "99%", "$50M"',
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'label',
      title: 'Label',
      type: 'internationalizedArrayString',
      description: 'e.g., "Customers", "Satisfaction Rate", "Revenue"',
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'description',
      title: 'Description',
      type: 'internationalizedArrayText',
      description: 'Optional longer description for the metric.',
    }),
  ],
  preview: {
    select: {
      title: 'value.0.value',
      subtitle: 'label.0.value',
    },
    prepare({title, subtitle}) {
      return {
        title: title || 'Untitled Metric',
        subtitle: subtitle,
      }
    },
  },
})