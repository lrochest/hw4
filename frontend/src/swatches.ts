// Approximate swatch colors for the catalogue's color names ("heather gray",
// "navy blue"...). Only for the little dots on the product page; the name is
// always shown next to them.
const SWATCHES: [string, string][] = [
  ['dark heather', '#4a4f57'],
  ['charcoal', '#3b3f45'],
  ['heather gray', '#a7a9ac'],
  ['light gray', '#cfd2d6'],
  ['gray', '#9a9ea3'],
  ['grey', '#9a9ea3'],
  ['navy', '#14254a'],
  ['light blue', '#8fb8de'],
  ['royal', '#2451a6'],
  ['blue', '#2f5d9a'],
  ['white', '#ffffff'],
  ['cream', '#efe6d2'],
  ['black', '#111111'],
  ['red', '#b3242b'],
  ['maroon', '#6b1f2a'],
  ['coral', '#e98672'],
  ['yellow', '#e7c23c'],
  ['gold', '#c9a227'],
  ['green', '#2f6b3f'],
  ['orange', '#e57a2e'],
  ['pink', '#f2a7bb'],
  ['purple', '#6a4c93'],
  ['brown', '#7a5536'],
]

export function swatchFor(color: string): string {
  const name = color.toLowerCase()
  return SWATCHES.find(([key]) => name.includes(key))?.[1] ?? '#c8c8c8'
}
