import type { Product } from './api.ts'

// Shopper-facing collections, matched on product names. The catalogue has no
// collection column, and generic tags like "college merch" appear on almost
// every item, so names are the reliable signal.

export interface Collection {
  slug: string
  title: string
  blurb: string
  pattern: RegExp
}

const RESIDENTIAL_COLLEGES = [
  'Benjamin Franklin', 'Berkeley', 'Branford', 'Davenport', 'Ezra Stiles', 'Grace Hopper',
  'Jonathan Edwards', 'Morse', 'Pauli Murray', 'Pierson', 'Saybrook', 'Silliman',
  'Timothy Dwight', 'Trumbull',
]

const SPORTS = [
  'baseball', 'basketball', 'diving', 'fencing', 'field hockey', 'football', 'golf', 'hockey',
  'lacrosse', 'sailing', 'soccer', 'squash', 'swimming', 'tennis', 'track', 'volleyball',
]

const FAMILY = ['mom', 'dad', 'grandma', 'grandpa', 'aunt', 'uncle', 'brother', 'sister', 'cousin']

const words = (list: string[]) => new RegExp(`\\b(${list.join('|')})\\b`, 'i')

export const COLLECTIONS: Collection[] = [
  {
    slug: 'colleges',
    title: 'Your residential college',
    blurb: 'Crests for Berkeley, Branford, Davenport, Grace Hopper, Morse, Saybrook and more.',
    pattern: words(RESIDENTIAL_COLLEGES),
  },
  {
    slug: 'sports',
    title: 'Your team',
    blurb: 'Left-chest marks and sports tees for everything from squash to sailing.',
    pattern: words(SPORTS),
  },
  {
    slug: 'family',
    title: 'Your family',
    blurb: 'Mom, Dad, Grandpa, Aunt, Cousin. Everyone who drove you to move-in.',
    pattern: words(FAMILY),
  },
  {
    slug: 'schools',
    title: 'Your school',
    blurb: 'Law, Medicine, Management, Art, Music, Nursing and the other graduate schools.',
    pattern: /\b(school|divinity)\b/i,
  },
]

export function inCollection(product: Product, slug: string): boolean {
  const collection = COLLECTIONS.find((c) => c.slug === slug)
  return collection ? collection.pattern.test(product.name) : true
}

// A short label for a product card's corner badge, from its collection.
const BADGES: [RegExp, string][] = [
  [/\b(harvard|the game)\b/i, 'The Game'],
  [words(FAMILY), 'Family'],
  [words(RESIDENTIAL_COLLEGES), 'Res. college'],
  [/\b(school|divinity)\b/i, 'Grad school'],
  [words(SPORTS), 'Varsity'],
  [/\bbulldog\b/i, 'Bulldog'],
]

export function badgeFor(product: Product): string | null {
  return BADGES.find(([pattern]) => pattern.test(product.name))?.[1] ?? null
}
