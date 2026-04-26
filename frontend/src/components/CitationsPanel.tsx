import React from 'react'
import { Citation } from '../services/api'
import styles from './CitationsPanel.module.css'

interface CitationsPanelProps {
  citations: Citation[]
}

export const CitationsPanel: React.FC<CitationsPanelProps> = ({ citations }) => {
  if (!citations || citations.length === 0) {
    return (
      <div className={styles.container}>
        <h4>Citations</h4>
        <p className={styles.empty}>No citations for this response</p>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <h4>Citations ({citations.length})</h4>
      <div className={styles.citationList}>
        {citations.map((citation, index) => (
          <div key={`${citation.doc_id}-${index}`} className={styles.citation}>
            <div className={styles.citationHeader}>
              <span className={styles.number}>{index + 1}</span>
              <div className={styles.titlePath}>
                <h5 className={styles.title}>{citation.title}</h5>
                <span className={styles.path}>{citation.path}</span>
              </div>
            </div>
            <p className={styles.content}>{citation.content}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
