import React from 'react'
import styles from './VariantSelector.module.css'

export interface Variant {
  id: string
  name: string
  description: string
}

const VARIANTS: Variant[] = [
  {
    id: 'CloudNative',
    name: 'Cloud Native',
    description: 'Cloud-native deployment documentation',
  },
  {
    id: 'ServerBased',
    name: 'Server-Based',
    description: 'On-premises server deployment documentation',
  },
]

interface VariantSelectorProps {
  selectedVariant: string
  onVariantChange: (variant: string) => void
}

export const VariantSelector: React.FC<VariantSelectorProps> = ({
  selectedVariant,
  onVariantChange,
}) => {
  return (
    <div className={styles.container}>
      <label className={styles.label}>Documentation Variant</label>
      <div className={styles.selector}>
        {VARIANTS.map((variant) => (
          <button
            key={variant.id}
            className={`${styles.button} ${
              selectedVariant === variant.id ? styles.active : ''
            }`}
            onClick={() => onVariantChange(variant.id)}
            title={variant.description}
          >
            <span className={styles.name}>{variant.name}</span>
            <span className={styles.description}>{variant.description}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
