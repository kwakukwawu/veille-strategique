import os
import sqlite3

def _pick_db_path() -> str:
    candidates = [
        os.path.join('instance', 'veille_strategique.db'),
        os.path.join('backend', 'instance', 'veille_strategique.db'),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]

def _score_source(row):
    # row: (id, nom, type_scraper, actif)
    _id, _nom, _type, _actif = row
    t = (_type or '').strip()
    # Prefer dedicated scrapers (non-structures), then structures, then empty
    if t and t != 'structures':
        return (3, -_id)
    if t == 'structures':
        return (2, -_id)
    return (1, -_id)

def main():
    db_path = _pick_db_path()
    print('DB', db_path)

    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute('PRAGMA busy_timeout=60000')
    cur = conn.cursor()

    cur.execute(
        "SELECT url_base, COUNT(*) as c "
        "FROM sources "
        "WHERE url_base IS NOT NULL AND TRIM(url_base) <> '' "
        "GROUP BY url_base HAVING c > 1"
    )
    groups = cur.fetchall()
    print('DUP_GROUPS', len(groups))

    deleted = 0
    for url_base, count in groups:
        cur.execute(
            "SELECT id, nom, type_scraper, actif FROM sources WHERE url_base=? ORDER BY id ASC",
            (url_base,),
        )
        rows = cur.fetchall()
        keeper = max(rows, key=_score_source)
        keeper_id = keeper[0]

        # Ensure keeper stays active and has a scraper type
        keeper_type = (keeper[2] or '').strip()
        if not keeper_type:
            cur.execute("UPDATE sources SET type_scraper=? WHERE id=?", ('structures', keeper_id))
        cur.execute("UPDATE sources SET actif=1 WHERE id=?", (keeper_id,))

        for row in rows:
            if row[0] == keeper_id:
                continue
            cur.execute("DELETE FROM sources WHERE id=?", (row[0],))
            deleted += 1

        print('URL', url_base, 'count', count, 'keeper', keeper_id)

    conn.commit()
    conn.close()
    print('DELETED', deleted)

if __name__ == '__main__':
    main()
