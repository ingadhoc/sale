const DB_NAME = "sale_offline_app";
const DB_VERSION = 1;
const STORES = { meta: "key", partners: "id", products: "id", orders: "uuid" };

function requestToPromise(request) {
    return new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

function transactionToPromise(transaction) {
    return new Promise((resolve, reject) => {
        transaction.oncomplete = () => resolve();
        transaction.onerror = () => reject(transaction.error);
        transaction.onabort = () => reject(transaction.error);
    });
}

/**
 * Minimal IndexedDB wrapper: one object store per kind of record.
 * Unlike web's IndexedDB util, a schema change never wipes the database,
 * so pending orders survive app updates.
 */
export class LocalDB {
    async open() {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        request.onupgradeneeded = () => {
            const db = request.result;
            for (const [name, keyPath] of Object.entries(STORES)) {
                if (!db.objectStoreNames.contains(name)) {
                    db.createObjectStore(name, { keyPath });
                }
            }
        };
        this.db = await requestToPromise(request);
    }

    getAll(store) {
        return requestToPromise(this.db.transaction(store).objectStore(store).getAll());
    }

    async getMeta(key) {
        const record = await requestToPromise(this.db.transaction("meta").objectStore("meta").get(key));
        return record?.value;
    }

    setMeta(key, value) {
        return this.put("meta", { key, value });
    }

    put(store, value) {
        const transaction = this.db.transaction(store, "readwrite");
        transaction.objectStore(store).put(value);
        return transactionToPromise(transaction);
    }

    clearAll() {
        const names = Object.keys(STORES);
        const transaction = this.db.transaction(names, "readwrite");
        for (const name of names) {
            transaction.objectStore(name).clear();
        }
        return transactionToPromise(transaction);
    }

    replaceAll(store, records) {
        const transaction = this.db.transaction(store, "readwrite");
        const objectStore = transaction.objectStore(store);
        objectStore.clear();
        for (const record of records) {
            objectStore.put(record);
        }
        return transactionToPromise(transaction);
    }
}
