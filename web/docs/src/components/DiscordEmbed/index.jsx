import React from 'react';
import styles from './styles.module.css';

export default function DiscordEmbed({ color = '#202225', title, description, children }) {
  return (
    <div className={styles.discordEmbed} style={{ borderLeftColor: color }}>
      <div className={styles.discordEmbedContent}>
        {title && <div className={styles.discordEmbedTitle}>{title}</div>}
        {description && <div className={styles.discordEmbedDescription}>{description}</div>}
        {children && <div className={styles.discordEmbedFields}>{children}</div>}
      </div>
    </div>
  );
}
