import {type SchemaTypeDefinition} from 'sanity'
import page from './documents/page'
import heroHeaderSection from './objects/heroHeaderSection'
import socialProofSection from './objects/socialProofSection'
import quoteSection from './objects/quoteSection'
import featuresSection from './objects/featuresSection'
import metricsSection from './objects/metricsSection'
import ctaSection from './objects/ctaSection'
import footer from './objects/footer'

export const schemaTypes: SchemaTypeDefinition[] = [heroHeaderSection, socialProofSection, quoteSection, featuresSection, metricsSection, ctaSection, footer, page]