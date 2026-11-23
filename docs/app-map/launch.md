---
title: Launch Module
sub: "The app starts, wires its dependencies and fills the plant catalog on first run."
card_title: Launch
card: App start, DI and the plant catalog seed
---

## What it does

`MainApplication` starts Hilt and gives WorkManager its configuration (DEBUG logging in debug builds, ERROR otherwise). `GardenActivity` draws edge-to-edge and hosts the whole Compose UI inside `SunflowerTheme`; `SunFlowerNavHost` opens on the `home` route. The Room database `sunflower-db` holds two tables, `plants` and `garden_plantings`. The first time it is created, a one-time `SeedDatabaseWorker` reads `plants.json` from the app's assets and upserts every plant, so the catalog appears shortly after the first launch. Hilt's `DatabaseModule` and `NetworkModule` provide the database, its two DAOs and the Unsplash service as singletons the other modules share.

## Logic · class diagram {#classes}

The activity only hosts Compose; the data layer is built once by Hilt and seeded by a background worker.

```mermaid
classDiagram
  direction LR
  class MainApplication {
    <<service>>
    workManagerConfiguration
  }
  class GardenActivity {
    <<page>>
    onCreate(savedInstanceState)
  }
  class SunflowerApp { <<widget>> }
  class SunFlowerNavHost { <<widget>> }
  class DatabaseModule {
    <<service>>
    provideAppDatabase(context)
    providePlantDao(appDatabase)
    provideGardenPlantingDao(appDatabase)
  }
  class NetworkModule {
    <<service>>
    provideUnsplashService()
  }
  class AppDatabase {
    <<service>>
    getInstance(context)
    buildDatabase(context)
    plantDao()
    gardenPlantingDao()
  }
  class SeedDatabaseWorker {
    <<service>>
    doWork()
  }
  class PlantDao {
    <<interface>>
    upsertAll(plants)
  }
  class GardenPlantingDao { <<interface>> }
  class UnsplashService {
    <<interface>>
    create()
  }
  GardenActivity ..> SunflowerApp : setContent
  SunflowerApp *-- SunFlowerNavHost
  DatabaseModule ..> AppDatabase : getInstance()
  NetworkModule ..> UnsplashService : create()
  AppDatabase ..> SeedDatabaseWorker : enqueues on first create
  AppDatabase --> PlantDao : plantDao
  AppDatabase --> GardenPlantingDao : gardenPlantingDao
  SeedDatabaseWorker ..> PlantDao : upsertAll()
```

- `──▷` holds
- `┄┄▷` uses
- `◆──` contains

## Seed the plant catalog on first launch · sequence {#sequence}

Seeding runs only from Room's `onCreate` callback, so it happens once per install.

```mermaid
sequenceDiagram
  actor User
  participant Act as GardenActivity
  participant Mod as DatabaseModule
  participant DB as AppDatabase
  participant Seed as SeedDatabaseWorker
  participant Dao as PlantDao
  User->>Act: opens the app
  Act->>Act: onCreate(savedInstanceState)
  Act-->>User: shows HomeScreen (empty catalog)
  Mod->>DB: getInstance(context)
  DB->>DB: builds sunflower-db
  Note over DB: onCreate runs only when sunflower-db is first created
  DB->>Seed: enqueue with PLANT_DATA_FILENAME = plants.json
  Seed->>Seed: doWork()
  Seed->>Dao: upsertAll(plants)
  Dao-->>User: the plants Flow emits and the catalog fills in
```

## Key files {#files}

- `app/src/main/java/com/google/samples/apps/sunflower/MainApplication.kt` · Hilt app, WorkManager config
- `app/src/main/java/com/google/samples/apps/sunflower/GardenActivity.kt` · the single activity
- `app/src/main/java/com/google/samples/apps/sunflower/compose/SunflowerApp.kt` · nav host and share intent
- `app/src/main/java/com/google/samples/apps/sunflower/compose/Screen.kt` · route definitions
- `app/src/main/java/com/google/samples/apps/sunflower/di/` · Hilt database and network modules
- `app/src/main/java/com/google/samples/apps/sunflower/data/AppDatabase.kt` · Room database and seed callback
- `app/src/main/java/com/google/samples/apps/sunflower/workers/` · catalog seed worker
- `app/src/main/java/com/google/samples/apps/sunflower/utilities/Constants.kt` · database and asset names
- `app/src/main/java/com/google/samples/apps/sunflower/ui/` · theme, colors, type, shapes
- `app/src/main/assets/plants.json` · the seeded plant catalog
