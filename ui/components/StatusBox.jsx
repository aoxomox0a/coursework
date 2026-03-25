import { useStatus } from '../context/StatusContext';
import styles from '../styles/StatusBox.module.css';

export default function StatusBox({ statuses = null, onRemove = null }) {
  const context = useStatus();
  
  // Use provided statuses or fall back to context statuses
  const displayStatuses = statuses !== null ? statuses : context.statuses;
  const handleRemove = onRemove || context.removeStatus;

  if (!displayStatuses || displayStatuses.length === 0) {
    return null;
  }

  return (
    <div className={styles.listContainer}>
      {displayStatuses.map((item) => (
        <div key={item.id} className={styles.statusLine}>
          <span className={styles.bullet}>-</span>
          <span className={styles.text}>
            {item.message}
            {item.status === 'error' && item.details && (
              <div className={styles.errorDetails}>{item.details}</div>
            )}
          </span>
        </div>
      ))}
    </div>
  );
}
