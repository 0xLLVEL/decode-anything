<?php

namespace SpondonIt\Service\Services;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Services\DatabaseService.php
 */

class DatabaseService {
    public function validateConnection(array $params): bool {
        $dbConnection = config('spondonit.support_multi_connection', false) ? config('database.default', null) : null;
        $dbHost = config('database.connections.' . $dbConnection . '.host', 'localhost');
        $dbPort = config('database.connections.' . $dbConnection . '.port', 3306);
        $dbUsername = config('database.connections.' . $dbConnection . '.username');
        $dbPassword = config('database.connections.' . $dbConnection . '.password');
        $dbDatabase = config('database.connections.' . $dbConnection . '.database');
        try {
            if ($dbConnection === 'pgsql') {
                $link = @pg_connect('host=' . $dbHost . ' dbname=' . $dbDatabase . ' user=' . $dbUsername . ' password=' . $dbPassword . ' port=' . $dbPort);
            } else {
                $link = @mysqli_connect($dbHost, $dbUsername, $dbPassword, $dbDatabase, (int) $dbPort);
            }
        } catch (\Exception $e) {
            Illuminate\Support\Facades\Log::error($e);
            $link = false;
        }
        if (!$link) {
            throw Illuminate\Validation\ValidationException::withMessages([
                'message' => trans('service::install.connection_not_established'),
            ]);
        }
        $forceMigrate = !empty($params['force_migrate']);
        if (!$forceMigrate && $dbConnection !== 'pgsql') {
            $countTableQuery = mysqli_query($link, 'show tables');
            $countTable = mysqli_num_rows($countTableQuery);
            if ($countTable) {
                throw Illuminate\Validation\ValidationException::withMessages([
                    'message' => trans('service::install.existing_table_in_database'),
                ]);
            }
        }
        $this->writeEnv($params);
        if ($forceMigrate) {
            $this->wipe();
        }
        return true;
    }

    public function checkExistingConnection(): bool {
        $dbConnection = config('spondonit.support_multi_connection', false) ? config('database.default', null) : null;
        $dbHost = config('database.connections.' . $dbConnection . '.host', 'localhost');
        $dbPort = config('database.connections.' . $dbConnection . '.port', 3306);
        $dbUsername = config('database.connections.' . $dbConnection . '.username');
        $dbPassword = config('database.connections.' . $dbConnection . '.password');
        $dbDatabase = config('database.connections.' . $dbConnection . '.database');
        try {
            if ($dbConnection === 'pgsql') {
                $link = @pg_connect('host=' . $dbHost . ' dbname=' . $dbDatabase . ' user=' . $dbUsername . ' password=' . $dbPassword . ' port=' . $dbPort);
            } else {
                $link = @mysqli_connect($dbHost, $dbUsername, $dbPassword, $dbDatabase, (int) $dbPort);
            }
        } catch (\Exception $exception) {
            return false;
        }
        if (!$link) {
            return false;
        }
        if ($dbConnection !== 'pgsql') {
            $countTableQuery = mysqli_query($link, 'show tables');
            $countTable = mysqli_num_rows($countTableQuery);
            if ($countTable) {
                return false;
            }
        }
        return true;
    }

    public function writeEnv(array $params): void {
        $dbConnection = config('spondonit.support_multi_connection', false) ? $params['db_connection'] ?? null : null;
        updateEnvFile([
            'APP_URL' => appUrl(),
            'DB_CONNECTION' => $dbConnection,
            'DB_PORT' => $params['db_port'] ?? 3306,
            'DB_HOST' => $params['db_host'] ?? 'localhost',
            'DB_DATABASE' => $params['db_database'] ?? '',
            'DB_USERNAME' => $params['db_username'] ?? '',
            'DB_PASSWORD' => $params['db_password'] ?? '',
        ]);
        Illuminate\Support\Facades\DB::disconnect($dbConnection);
        config([
            'database.connections.' . $dbConnection . '.host' => $params['db_host'] ?? 'localhost',
            'database.connections.' . $dbConnection . '.port' => $params['db_port'] ?? 3306,
            'database.connections.' . $dbConnection . '.database' => $params['db_database'] ?? '',
            'database.connections.' . $dbConnection . '.username' => $params['db_username'] ?? '',
            'database.connections.' . $dbConnection . '.password' => $params['db_password'] ?? '',
        ]);
        Illuminate\Support\Facades\DB::setDefaultConnection($dbConnection);
    }

    public function migrate(): bool {
        Illuminate\Support\Facades\Artisan::call('migrate:fresh', ['--force' => true]);
        try {
            return true;
        } catch (\Exception $e) {
            $this->wipe();
            Illuminate\Support\Facades\Log::error($e);
            return false;
        }
    }

    public function wipe(): void {
        Illuminate\Support\Facades\Artisan::call('db:wipe', ['--force' => true]);
    }

    public function seed(bool $shouldSeed = false): void {
        if (!$shouldSeed) {
            return;
        }
        Illuminate\Support\Facades\Artisan::call('db:seed', ['--force' => true]);
    }
}
