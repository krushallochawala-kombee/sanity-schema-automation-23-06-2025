import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'metricsSection',
  title: 'Metrics Section',
  type: 'object',
  fields: [
    defineField({
      name: 'overlineHeading',
      title: 'Overline Heading',
      type: 'internationalizedArrayString',
    }),
    defineField({
      name: 'heading',
      title: 'Main Heading',
      type: 'internationalizedArrayString',
    }),
    defineField({
      name: 'description',
      title: 'Description Text',
      type: 'internationalizedArrayText',
    }),
    defineField({
      name: 'metrics',
      title: 'Metrics',
      type: 'array',
      of: [
        defineField({
          name: 'metricItem',
          title: 'Metric Item',
          type: 'object',
          fields: [
            defineField({
              name: 'value',
              title: 'Value',
              type: 'internationalizedArrayString',
              description: "The large metric number or text (e.g., '4,000+', '600%').",
            }),
            defineField({
              name: 'label',
              title: 'Label',
              type: 'internationalizedArrayString',
              description: "The small title for the metric (e.g., 'Global customers').",
            }),
            defineField({
              name: 'description',
              title: 'Description',
              type: 'internationalizedArrayText',
              description:
                "A short descriptive text for the metric (e.g., 'We've helped over 4,000 amazing global companies.').",
            }),
          ],
        }),
      ],
    }),
    defineField({
      name: 'image',
      title: 'Section Image',
      type: 'image',
      options: {hotspot: true},
    }),
  ],
})
