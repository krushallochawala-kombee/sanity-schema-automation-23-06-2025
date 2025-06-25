import {defineConfig} from 'sanity'
import {structureTool} from 'sanity/structure'
import {internationalizedArray} from 'sanity-plugin-internationalized-array'
import {schemaTypes} from './schemaTypes/index'

const SUPPORTED_LOCALES = [
  {id: 'en', title: 'English'},
  {id: 'hin', title: 'Hindi'},
]

export default defineConfig({
  name: 'default',
  title: 'schema-automation-23-06-25',

  projectId: 'szpg7yxe',
  dataset: 'production',

  plugins: [
    structureTool(),
    internationalizedArray({
      languages: SUPPORTED_LOCALES,
      defaultLanguages: ['en'],
      fieldTypes: ['string', 'text'],
    }),
  ],

  schema: {
    types: schemaTypes,
  },
})
