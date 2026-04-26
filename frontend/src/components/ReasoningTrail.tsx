import React, { useState } from 'react'
import { QueryResponse } from '../services/api'
import styles from './ReasoningTrail.module.css'

interface ReasoningTrailProps {
  response: QueryResponse
}

export const ReasoningTrail: React.FC<ReasoningTrailProps> = ({ response }) => {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className={styles.container}>
      <div
        className={styles.header}
        onClick={() => setExpanded(!expanded)}
        role="button"
        tabIndex={0}
      >
        <span className={styles.icon}>
          {expanded ? '▼' : '▶'}
        </span>
        <span className={styles.title}>Reasoning Trail</span>
        <span className={styles.subtitle}>
          {response.tool_calls} tool calls · {response.processing_time.toFixed(2)}s
        </span>
      </div>

      {expanded && (
        <div className={styles.content}>
          <div className={styles.info}>
            <div className={styles.infoRow}>
              <span className={styles.label}>Variant:</span>
              <span className={styles.value}>{response.variant}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.label}>Tool Calls:</span>
              <span className={styles.value}>{response.tool_calls}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.label}>Processing Time:</span>
              <span className={styles.value}>
                {response.processing_time.toFixed(2)}s
              </span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.label}>Session ID:</span>
              <span className={styles.sessionId}>
                {response.session_id.substring(0, 8)}...
              </span>
            </div>
          </div>

          <div className={styles.section}>
            <h5>Processing Steps</h5>
            <ol className={styles.stepsList}>
              <li className={styles.step}>
                <span className={styles.stepIcon}>1</span>
                <div>
                  <strong>Query Processing</strong>
                  <p className={styles.stepDesc}>Parsed and validated input query</p>
                </div>
              </li>
              <li className={styles.step}>
                <span className={styles.stepIcon}>2</span>
                <div>
                  <strong>Planning</strong>
                  <p className={styles.stepDesc}>
                    Determined relevant tools and search terms
                  </p>
                </div>
              </li>
              <li className={styles.step}>
                <span className={styles.stepIcon}>3</span>
                <div>
                  <strong>Execution</strong>
                  <p className={styles.stepDesc}>
                    Executed {response.tool_calls} tool calls
                  </p>
                </div>
              </li>
              <li className={styles.step}>
                <span className={styles.stepIcon}>4</span>
                <div>
                  <strong>Synthesis</strong>
                  <p className={styles.stepDesc}>
                    Generated answer and extracted citations
                  </p>
                </div>
              </li>
            </ol>
          </div>
        </div>
      )}
    </div>
  )
}
