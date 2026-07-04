import React from 'react';

const DiscordMention = ({ text }) => {
  if (!text) return null;
  
  // Regex to match <@id>, <@!id>, <@&id>, <#id>
  const mentionRegex = /<(@!|@&|@|#)(\d+)>/g;
  
  const parts = [];
  let lastIndex = 0;
  let match;
  
  while ((match = mentionRegex.exec(text)) !== null) {
    // Push preceding text
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    
    const type = match[1]; // @, @&, #
    const id = match[2];
    
    let label = id;
    let bgColor = 'rgba(88, 101, 242, 0.2)';
    let color = '#5865F2';
    
    if (type === '#') {
      label = `#kanal-${id.slice(0,4)}`;
      bgColor = 'rgba(43, 45, 49, 0.8)';
      color = '#e3e5e8';
    } else if (type === '@&') {
      label = `@Rol-${id.slice(0,4)}`;
      bgColor = 'rgba(235, 69, 158, 0.2)';
      color = '#eb459e';
    } else {
      label = `@kullanıcı-${id.slice(0,4)}`;
      bgColor = 'rgba(88, 101, 242, 0.2)';
      color = '#c9cdfb';
    }
    
    parts.push(
      <span key={match.index} style={{
        background: bgColor,
        color: color,
        padding: '2px 6px',
        borderRadius: '4px',
        fontSize: '0.9em',
        fontWeight: '500',
        fontFamily: 'monospace'
      }} title={id}>
        {label}
      </span>
    );
    
    lastIndex = mentionRegex.lastIndex;
  }
  
  // Push remaining text
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }
  
  return (
    <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', display: 'inline' }}>
      {parts.map((part, i) => {
        if (typeof part === 'string') {
          return <React.Fragment key={i}>{part}</React.Fragment>;
        }
        return part;
      })}
    </div>
  );
};

export default DiscordMention;
