import {defineType, defineField} from 'sanity'
export default defineType({
    name: 'page', title: 'Page', type: 'document',
    fields: [
        defineField({name: 'title', title: 'Title', type: 'string'}),
        defineField({name: 'slug', title: 'Slug', type: 'slug', options: {source: 'title'}}),
        defineField({name: 'pageBuilder', title: 'Page Builder', type: 'array', of: [{type: 'heroHeaderSection'}, {type: 'socialProofSection'}, {type: 'quoteSection'}, {type: 'featuresSection'}, {type: 'metricsSection'}, {type: 'ctaSection'}, {type: 'footer'}] })
    ]
})