# OPS-12 — 백업을 다른 볼륨에 두고, 거기서 읽었다 (2026-09-06 16:01:13)

**이 파일은 `scripts/ops_backup_volume.py` 가 실행하며 적었다.**
아래 rc·바이트·해시는 전부 그 실행의 것이다.

## 0. 무엇을 만들고 어떻게 지우는가 — **하기 전에 적는다**

만드는 것: 도커 볼륨 `gx_backup_vault_e` 하나. 쓰는 컨테이너는 `--rm` 이라 남지 않는다.
건드리지 않는 것: `postgres` · `gx-shell` · `redis` · MinIO (다른 차선이 쓴다) ·
그리고 DB 데이터 볼륨 `gx_pgdata` — **붙이지도 않는다.**
지우는 법: `docker volume rm gx_backup_vault_e` — 이 한 줄이면 원상태다.

빌려 온 자격증명: `gx-shell` 컨테이너의 DB_HOST · DB_NAME · DB_PASSWORD · DB_PORT · DB_USER. **값은 여기 적지 않는다**(D-204).

## 1. 목적지 볼륨을 만든다

```
docker volume create gx_backup_vault_e        rc=0
목적지 볼륨의 자리: /var/lib/docker/volumes/gx_backup_vault_e/_data
DB 데이터 볼륨의 자리: /var/lib/docker/volumes/gx_pgdata/_data
```

## 2. **다른 볼륨으로** 뜬다 — 판이 맞는 클라이언트로

판이 맞아야 한다 [실측 2026-09-09]: 앱 컨테이너의 `pg_dump` 가 서버보다 낮으면
`aborting because of server version mismatch` 로 죽는다. 그래서 **DB 컨테이너와
같은 이미지**(`postgres:latest`)를 하나 띄워 그 안의 `pg_dump` 를 쓴다.

```
docker run --rm --network gx-main-network -v gx_backup_vault_e:/backup \
    -e PGPASSWORD=**** postgres:latest \
    pg_dump -h postgres -p 5432 -U postgres -d database_guardianx -Fc -f /backup/database_guardianx_20260906T160107.dump
rc=0
```

## 3. **다른 컨테이너**에서 그 볼륨만 붙여 읽는다

방금 뜬 컨테이너는 이미 사라졌다(`--rm`). 여기서 다시 띄우는 것은 **그 볼륨만**
아는 새 컨테이너다 — DB 에도 안 붙는다. 「목적지에 남았고, 거기서 읽힌다」를
보는 것이 이 단계의 전부다.

```
docker run --rm -v gx_backup_vault_e:/backup postgres:latest sh -c '<ls · sha256sum · pg_restore --list | wc -l>'
-rw-r--r-- 1 root root 9209410 Sep  6 07:01 /backup/database_guardianx_20260906T160107.dump
ef9b9e6eb2dae9f7d8a20eefce09259398e08cc71256997b36e0550090871031  /backup/database_guardianx_20260906T160107.dump   # sha256sum 출력 — 내용 해시이지 자격증명이 아니다
3351
rc=0
```

## 4. 저장소 안에 있는가 — **없어야 한다**

이번 덤프(`database_guardianx_20260906T160107.dump`)가 저장소 작업복사본 안에 있는가: **없다**

★ 그리고 **옛 백업이 아직 저장소 안에 있다** — 이것이 OPS-12 가 말하던 빚이다.
  `*database_guardianx*.dump` 로 저장소를 훑으니 **1건**:
  · docs\agent\evidence\D-354\backup\db_database_guardianx_20260829T134442Z.dump
  이 갈래(볼륨)가 그 자리를 대신할 수 있다는 것을 이 실행이 보였다. **옮기는 것은
  이 스크립트가 하지 않는다** — 지우는 일에는 되돌림이 없고, 무엇을 남길지는
  보존 정책(OPS-07)이 정할 일이다.

## 5. 판정

  OK   ① 떴는가            덤프 9,209,410바이트
  OK   ② 다른 볼륨인가        목적지 'gx_backup_vault_e' · DB 데이터 'gx_pgdata' — 다르다
  OK   ③ 저장소 밖인가        이번 덤프는 저장소 작업복사본 안에 없다
  OK   ④ 거기서 읽히는가       다른 컨테이너에서 `pg_restore --list` 목차 3351줄

파일 이름 `database_guardianx_20260906T160107.dump` · sha256 `ef9b9e6eb2dae9f7d8a20eefce09259398e08cc71256997b36e0550090871031`
판정 **통과**

## 6. 아직 못 넘은 것 — **다른 호스트**

이것은 **볼륨 갈래**다. 호스트 갈래가 아니다. 이 기계에는 목적지가 될 두 번째
호스트가 없고, 없는 것을 있다고 적지 않는다(D-286). 볼륨을 갈랐다는 사실은
「저장소와 함께 죽지 않는다」까지 말하고, 「이 기계와 함께 죽지 않는다」는
**말하지 않는다.** 그 절반은 배포 형상이 정해질 때 갚는다.
