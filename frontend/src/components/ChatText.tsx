import { Fragment, type ReactNode } from 'react'

// Renders the small bit of Markdown the agent is allowed to use (**bold** and
// "- " bullet lines) as React elements. No HTML is ever injected, so a reply
// can't smuggle in markup or scripts.

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((piece, i) =>
    piece.startsWith('**') && piece.endsWith('**') && piece.length > 4 ? (
      <strong key={i}>{piece.slice(2, -2)}</strong>
    ) : (
      <Fragment key={i}>{piece}</Fragment>
    ),
  )
}

export default function ChatText({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let bullets: string[] = []

  const flush = () => {
    if (bullets.length) {
      blocks.push(
        <ul key={`ul-${blocks.length}`}>
          {bullets.map((b, i) => (
            <li key={i}>{inline(b)}</li>
          ))}
        </ul>,
      )
      bullets = []
    }
  }

  for (const line of text.split('\n')) {
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/)
    if (bullet) {
      bullets.push(bullet[1])
    } else {
      flush()
      if (line.trim()) blocks.push(<p key={`p-${blocks.length}`}>{inline(line)}</p>)
    }
  }
  flush()

  return <>{blocks}</>
}
