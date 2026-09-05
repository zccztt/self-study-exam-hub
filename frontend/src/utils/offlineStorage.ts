const DB_NAME = 'exam-hub-offline'
const DB_VERSION = 1
const STORES = ['questions', 'analysis', 'videos', 'examResults'] as const
type StoreName = typeof STORES[number]

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      STORES.forEach(store => {
        if (!db.objectStoreNames.contains(store)) {
          db.createObjectStore(store, { keyPath: 'id' })
        }
      })
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

export async function saveOffline<T extends { id: number | string }>(store: StoreName, data: T | T[]): Promise<void> {
  const db = await openDB()
  const tx = db.transaction(store, 'readwrite')
  const objStore = tx.objectStore(store)
  const items = Array.isArray(data) ? data : [data]
  items.forEach(item => objStore.put(item))
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function getOffline<T>(store: StoreName, id: number | string): Promise<T | undefined> {
  const db = await openDB()
  const tx = db.transaction(store, 'readonly')
  const objStore = tx.objectStore(store)
  return new Promise((resolve, reject) => {
    const req = objStore.get(id)
    req.onsuccess = () => resolve(req.result as T | undefined)
    req.onerror = () => reject(req.error)
  })
}

export async function getAllOffline<T>(store: StoreName): Promise<T[]> {
  const db = await openDB()
  const tx = db.transaction(store, 'readonly')
  const objStore = tx.objectStore(store)
  return new Promise((resolve, reject) => {
    const req = objStore.getAll()
    req.onsuccess = () => resolve(req.result as T[])
    req.onerror = () => reject(req.error)
  })
}

export async function clearOfflineStore(store: StoreName): Promise<void> {
  const db = await openDB()
  const tx = db.transaction(store, 'readwrite')
  tx.objectStore(store).clear()
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export function isOnline(): boolean {
  return navigator.onLine
}
