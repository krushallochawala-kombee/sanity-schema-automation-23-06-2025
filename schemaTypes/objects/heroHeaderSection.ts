import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'heroHeaderSection',
  title: 'Hero Header Section',
  type: 'object',
  fields: [
    defineField({
      name: 'hasAnnouncementBadge',
      title: 'Display Announcement Badge?',
      type: 'boolean',
    }),
    defineField({
      name: 'badgeText',
      title: 'Badge Text',
      type: 'internationalizedArrayString',
    }),
    defineField({
      name: 'badgeLinkText',
      title: 'Badge Link Text',
      type: 'internationalizedArrayString',
    }),
    defineField({
      name: 'badgeLinkUrl',
      title: 'Badge Link URL',
      type: 'url',
    }),
    defineField({
      name: 'heroTitle',
      title: 'Hero Title',
      type: 'internationalizedArrayString',
    }),
    defineField({
      name: 'heroDescription',
      title: 'Hero Description',
      type: 'internationalizedArrayText',
    }),
    defineField({
      name: 'ctaText',
      title: 'Call To Action Button Text',
      type: 'internationalizedArrayString',
    }),
    defineField({
      name: 'ctaUrl',
      title: 'Call To Action Button URL',
      type: 'url',
    }),
    defineField({
      name: 'ctaIcon',
      title: 'Call To Action Button Icon',
      type: 'image',
      options: {hotspot: true},
    }),
    defineField({
      name: 'mockupImage',
      title: 'Hero Mockup Image',
      type: 'image',
      options: {hotspot: true},
    }),
  ],
})
