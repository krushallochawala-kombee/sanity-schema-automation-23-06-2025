import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'page',
  title: 'Page',
  type: 'document',
  fields: [
    defineField({
      name: 'title',
      title: 'Title',
      type: 'internationalizedArrayString',
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'slug',
      title: 'Slug',
      type: 'internationalizedArraySlug',
      options: {
        source: 'title.0.value',
        maxLength: 96,
      },
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'description',
      title: 'Description (SEO)',
      type: 'internationalizedArrayText',
      description: 'A brief description for search engine optimization.',
    }),
    defineField({
      name: 'pageBuilder',
      title: 'Page Sections',
      type: 'array',
      of: [
        {type: 'ctasection'},
        {type: 'featuressection'},
        {type: 'herosection'},
        {type: 'metricssection'},
        {type: 'quotesection'},
        {type: 'socialproofsection'},
      ],
      validation: (Rule) => Rule.required().min(1),
    }),
  ],
  preview: {
    select: {
      title: 'title.0.value',
      subtitle: 'slug.0.current',
    },
    prepare({title, subtitle}) {
      return {
        title: title || 'Untitled Page',
        subtitle: subtitle ? `/${subtitle}` : 'No slug',
      }
    },
  },
})