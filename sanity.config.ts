import {defineConfig} from 'sanity'
import {structureTool} from 'sanity/structure'
import {internationalizedArray} from 'sanity-plugin-internationalized-array'
import {schemaTypes} from './schemaTypes1/index'
import {visionTool} from '@sanity/vision'

const SUPPORTED_LOCALES = [
  {id: 'en', title: 'English'},
  {id: 'hin', title: 'Hindi'},
]

export default defineConfig({
  name: 'default',
  title: 'schema-automation-23-06-25',

  projectId: process.env.SANITY_PROJECT_ID || '',
  dataset: process.env.SANITY_DATASET || '',

  plugins: [
    structureTool(),
    visionTool(),
    internationalizedArray({
      languages: SUPPORTED_LOCALES,
      defaultLanguages: ['en'],
      fieldTypes: ['string', 'text', 'image', 'url', 'file', 'slug'],
    }),
  ],

  schema: {
    types: schemaTypes,
  },
})
