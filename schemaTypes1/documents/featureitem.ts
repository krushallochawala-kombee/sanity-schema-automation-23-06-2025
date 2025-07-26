import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'featureitem',
  title: 'Feature Item',
  type: 'document',
  fields: [
    defineField({
      name: 'title',
      title: 'Title',
      type: 'internationalizedArrayString',
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'description',
      title: 'Description',
      type: 'internationalizedArrayText',
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'icon',
      title: 'Icon',
      type: 'internationalizedArrayImage',
      options: {
        hotspot: true,
      },
    }),
  ],
  preview: {
    select: {
      title: 'title.0.value',
      subtitle: 'description.0.value',
      media: 'icon.0.value.asset',
    },
    prepare({title, subtitle, media}) {
      return {
        title: title || 'Untitled Feature Item',
        subtitle: subtitle,
        media: media,
      }
    },
  },
})