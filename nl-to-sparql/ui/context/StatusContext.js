import { createContext, useContext, useState, useCallback } from 'react';

const StatusContext = createContext();

export function StatusProvider({ children }) {
  const [statuses, setStatuses] = useState([]); // Array of status messages

  const addStatus = useCallback((newStatus, newMessage, newDetails = '', newProgress = 0) => {
    const id = Date.now();
    const statusItem = {
      id,
      status: newStatus,
      message: newMessage,
      details: newDetails,
      progress: newProgress,
      timestamp: new Date(),
    };

    setStatuses((prev) => [...prev, statusItem]);

    // Auto-remove error messages after 6 seconds
    if (newStatus === 'error') {
      setTimeout(() => {
        setStatuses((prev) => prev.filter((s) => s.id !== id));
      }, 6000);
    }

    return id;
  }, []);

  const updateStatus = useCallback((statusId, newStatus, newMessage, newDetails = '', newProgress = 0) => {
    setStatuses((prev) =>
      prev.map((s) =>
        s.id === statusId
          ? {
              ...s,
              status: newStatus,
              message: newMessage,
              details: newDetails,
              progress: newProgress,
            }
          : s
      )
    );
  }, []);

  const removeStatus = useCallback((statusId) => {
    setStatuses((prev) => prev.filter((s) => s.id !== statusId));
  }, []);

  const clearAll = useCallback(() => {
    setStatuses([]);
  }, []);

  const value = {
    statuses,
    addStatus,
    updateStatus,
    removeStatus,
    clearAll,
  };

  return (
    <StatusContext.Provider value={value}>
      {children}
    </StatusContext.Provider>
  );
}

export function useStatus() {
  const context = useContext(StatusContext);
  if (!context) {
    throw new Error('useStatus must be used within a StatusProvider');
  }
  return context;
}
