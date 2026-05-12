interface Props {
  text: string
  className?: string
}

function renderLine(line: string): (string | { bold?: string; italic?: string })[] {
  const parts: (string | { bold?: string; italic?: string })[] = []
  let remaining = line

  const regex = /\[\[([BI])\]\](.*?)\[\[\/([BI])\]\]/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(remaining)) !== null) {
    if (match.index > lastIndex) {
      parts.push(remaining.slice(lastIndex, match.index))
    }
    const content = match[2]
    if (match[1] === 'B') {
      parts.push({ bold: content })
    } else {
      parts.push({ italic: content })
    }
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < remaining.length) {
    parts.push(remaining.slice(lastIndex))
  }

  return parts
}

export default function FormattedContent({ text, className = '' }: Props) {
  const paragraphs = text.split('\n\n')

  return (
    <div className={className}>
      {paragraphs.map((para, pi) => {
        const lines = para.split('\n')

        return (
          <p key={pi} style={{ marginBottom: '0.5em' }}>
            {lines.map((line, li) => {
              const parts = renderLine(line)
              return (
                <span key={li}>
                  {li > 0 && <br />}
                  {parts.map((part, idx) => {
                    if (typeof part === 'string') {
                      // Handle special markers
                      if (part === '*P.*' || part === '*T.*' || part === '*L.*') {
                        return <strong key={idx} style={{ color: 'var(--color-brand-gold, #B48A00)' }}>{part.slice(1, -1)}</strong>
                      }
                      if (part.startsWith('## ')) {
                        return <em key={idx} style={{ fontWeight: 700, color: 'var(--color-brand-gold, #B48A00)' }}>{part.slice(3)}</em>
                      }
                      return <span key={idx}>{part} </span>
                    }
                    if ('bold' in part) {
                      return <strong key={idx} style={{ fontWeight: 700 }}>{part.bold}</strong>
                    }
                    if ('italic' in part) {
                      return <em key={idx}>{part.italic}</em>
                    }
                    return null
                  })}
                </span>
              )
            })}
          </p>
        )
      })}
    </div>
  )
}
