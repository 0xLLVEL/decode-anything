<?php

namespace SpondonIt\Service\Services;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Services\InstallService.php
 */

if (class_exists('SpondonIt\\Service\\Repositories\\InstallRepository')) {
    $url = defined('INFIX_APP_URL') ? INFIX_APP_URL : 'https://codecanyon.net/item/infixlms-learning-management-system/30626608';
    $app_name = defined('INFIX_APP') ? INFIX_APP : 'CodeThemes - Portfolio';
    exit('You are using a deprecated application. Please update your code to use the application or contact the script author for more information. </br> Please visit <a href="' . $url . '">' . $app_name . ' </a> to purchase a license');
}

class InstallService {
    protected $preRequisiteChecker;
    protected $databaseService;
    protected $licenseVerifier;
    protected $lifecycle;

    public function __construct($preRequisiteChecker, $databaseService, $licenseVerifier, $lifecycle) {
        $this->preRequisiteChecker = $preRequisiteChecker;
        $this->databaseService = $databaseService;
        $this->licenseVerifier = $licenseVerifier;
        $this->lifecycle = $lifecycle;
    }

    public function checkInstallation(): void {
        $ac = Illuminate\Support\Facades\Storage::exists('.app_installed') ? Illuminate\Support\Facades\Storage::get('.app_installed') : null;
        if ($ac) {
            abort(404);
        }
    }

    public function checkReinstall(): bool {
        Illuminate\Support\Facades\DB::connection()->getPdo();
        try {
            return (int) (Illuminate\Support\Facades\Storage::exists('.install_count') ? Illuminate\Support\Facades\Storage::get('.install_count') : 0) && Illuminate\Support\Facades\Artisan::call('spondonit:migrate-status');
        } catch (\Exception $exception) {
            return false;
        }
    }

    public function getPreRequisite(): array {
        return $this->preRequisiteChecker->getPreRequisite();
    }

    public function validateDatabase(array $params): bool {
        return $this->databaseService->validateConnection($params);
    }

    public function checkDatabaseConnection(): bool {
        return $this->databaseService->checkExistingConnection();
    }

    public function setDBEnv(array $params): void {
        $this->databaseService->writeEnv($params);
    }

    public function migrateDB(): bool {
        return $this->databaseService->migrate();
    }

    public function rollbackDb(): void {
        $this->databaseService->wipe();
    }

    public function seed($seed = 0): void {
        $this->databaseService->seed((bool) $seed);
    }

    public function validateLicense(array $params) {
        return $this->licenseVerifier->validateLicense($params);
    }

    public function checkLicense(): ?bool {
        return $this->licenseVerifier->checkLicense();
    }

    public function install(array $params): void {
        @set_time_limit(0);
        @ini_set('max_execution_time', '0');
        if ($this->databaseService->migrate()) {
            $ac = Illuminate\Support\Facades\Storage::exists('.temp_app_installed') ? Illuminate\Support\Facades\Storage::get('.temp_app_installed') : null;
            Illuminate\Support\Facades\Storage::put('.app_installed', $ac ?? '');
            Illuminate\Support\Facades\Storage::put('.user_email', $params['email'] ?? '');
            Illuminate\Support\Facades\Storage::put('.user_pass', $params['password'] ?? '');
            Illuminate\Support\Facades\Storage::delete('.temp_app_installed');
            $this->lifecycle->afterAppInstall($params);
        } else {
            throw Illuminate\Validation\ValidationException::withMessages([
                'message' => 'There is something wrong in migration. Please contact the script author.',
            ]);
        }
    }

    public function uninstall(array $request): array {
        $signature = $request['signature'] ?? null;
        $dbConnection = config('spondonit.support_multi_connection', false) ? config('database.default', null) : null;
        $response = [
            'DB_CONNECTION' => config('database.default'),
            'DB_PORT' => config('database.connections.' . $dbConnection . '.port'),
            'DB_HOST' => config('database.connections.' . $dbConnection . '.host'),
            'DB_DATABASE' => config('database.connections.' . $dbConnection . '.database'),
            'DB_USERNAME' => config('database.connections.' . $dbConnection . '.username'),
            'DB_PASSWORD' => config('database.connections.' . $dbConnection . '.password'),
        ];
        if (config('app.signature') == $signature) {
            $defaultPort = $dbConnection === 'pgsql' ? 5432 : 3306;
            updateEnvFile([
                'DB_CONNECTION' => $dbConnection,
                'DB_PORT' => $defaultPort,
                'DB_HOST' => 'localhost',
                'DB_DATABASE' => '',
                'DB_USERNAME' => '',
                'DB_PASSWORD' => '',
            ]);
            Illuminate\Support\Facades\Storage::delete(['.access_code', '.account_email']);
            Illuminate\Support\Facades\Storage::put('.app_installed', '');
            Illuminate\Support\Facades\Artisan::call('optimize:clear');
            Illuminate\Support\Facades\Storage::put('.logout', true);
            $this->lifecycle->afterUninstall();
        }
        return $response;
    }

    public function installModule(array $params) {
        if (!config('spondonit.features.modules', false)) {
            return false;
        }
        $code = $params['purchase_code'] ?? null;
        $name = $params['name'] ?? null;
        $email = $params['envatouser'] ?? null;
        $row = !empty($params['row']);
        $file = !empty($params[null]);
        $dataPath = base_path('Modules/' . $name . '/' . $name . '.json');
        if (!Illuminate\Support\Facades\File::exists($dataPath)) {
            throw Illuminate\Validation\ValidationException::withMessages(['message' => 'Invalid module file. Please contact the script author.']);
        }
        $array = json_decode(Illuminate\Support\Facades\File::get($dataPath), true);
        $itemId = config('spondonit.modules.' . $name);
        if (!$itemId) {
            throw Illuminate\Validation\ValidationException::withMessages(['message' => 'Invalid module file. Please contact the script author.']);
        }
        $ve = $array[$name]['ve'] ?? 'e';
        $modulePath = storage_path('app/private/' . config('app.item') . '/' . '.' . $itemId);
        if (file_exists($modulePath)) {
            if (!$code) {
                $code = file_get_contents($modulePath);
            }
            $itemId = config('app.item');
        } elseif (!empty($params['tariq'])) {
            return false;
        }
        $verifier = $array[$name]['verifier'] ?? 'auth';
        $url = baseUrl($verifier) . '/api/cc?a=install' . '&u=' . appUrl() . '&ac=' . $code . '&i=' . $itemId . '&e=' . $email . '&t=Module' . '&ve=' . $ve . '&name=' . $name . '&row=' . ($row ? '1' : '0') . '&file=' . ($file ? '1' : '0') . '&current=' . str_replace(url('/') . '/', '', url()->previous()) . '&enc=1';
        $response = connectToServer($url);
        $goto = $response['goto'] ?? null;
        if ($goto) {
            if (request()->wantsJson()) {
                return $response;
            }
            redirect($goto)->send();
            return $response;
        }
        $status = !empty($response['status']);
        if ($status) {
            return $this->processModuleInstallation($params, $response);
        }
        $this->disableModule($name, $row, $file);
        throw Illuminate\Validation\ValidationException::withMessages(['message' => $response['message'] ?? 'Something is not right']);
        return null;
    }

    public function processModuleInstallation(array $params, array $response): array {
        $row = !empty($params['row']);
        $file = !empty($params[null]);
        $name = $params['name'] ?? '';
        $code = $params['ac'] ?? '';
        $email = $params['e'] ?? '';
        $dataPath = base_path('Modules/' . $name . '/' . $name . '.json');
        $array = json_decode(Illuminate\Support\Facades\File::get($dataPath), true);
        if (!$row) {
            if ($file) {
                app('general_settings')->put([$name => 0]);
            } elseif (!Illuminate\Support\Facades\Schema::hasColumn(config('spondonit.settings_table'), $name)) {
                Illuminate\Support\Facades\Schema::table(config('spondonit.settings_table'), function () use ($name) { /* closure body unavailable */ });
            }
        } else {
            $settingsModelClass = config('spondonit.settings_model');
            (new $settingsModelClass())->firstOrCreate(['key' => $name]);
        }
        $version = $array[$name]['versions'][0] ?? '1.0.0';
        $updateUrl = $array[$name]['url'][0] ?? '';
        $notes = $array[$name]['notes'][0] ?? '';
        Illuminate\Support\Facades\DB::beginTransaction();
        $moduleManagerClass = config('spondonit.module_manager_model');
        $moduleManager = (new $moduleManagerClass())->where('name', $name)->first();
        if (empty($moduleManager)) {
            $moduleManager = new $moduleManagerClass();
        }
        $moduleManager->name = $name;
        $moduleManager->email = $email;
        $moduleManager->notes = $notes;
        $moduleManager->version = $version;
        $moduleManager->update_url = $updateUrl;
        $moduleManager->installed_domain = appUrl();
        $moduleManager->activated_date = date('Y-m-d');
        $moduleManager->purchase_code = $code;
        $moduleManager->checksum = $response['checksum'] ?? null;
        $moduleManager->save();
        $settingsModelClass = config('spondonit.settings_model');
        if ($row) {
            $config = (new $settingsModelClass())->firstOrNew(['key' => $name]);
            $config->value = 1;
            $config->save();
        } elseif ($file) {
            app('general_settings')->put([$name => 1]);
        } else {
            $config = (new $settingsModelClass())->find(1);
            $config->{$name} = 1;
            $config->save();
        }
        Illuminate\Support\Facades\DB::commit();
        $this->lifecycle->afterModuleInstall($name, $params, $response);
        try {
            return $response;
        } catch (\Exception $e) {
            Illuminate\Support\Facades\DB::rollBack();
            Illuminate\Support\Facades\Log::error($e);
            $this->disableModule($name, $row, $file);
            throw Illuminate\Validation\ValidationException::withMessages(['message' => $e->getMessage()]);
        }
    }

    public function disableModule(string $moduleName, bool $row = false, bool $file = false): void {
        $settingsModelClass = config('spondonit.settings_model');
        if ($settingsModelClass) {
            if ($row) {
                $config = (new $settingsModelClass())->firstOrNew(['key' => $moduleName]);
                $config->value = 0;
                $config->save();
            } elseif ($file) {
                app('general_settings')->put([$moduleName => 0]);
            } else {
                if (!Illuminate\Support\Facades\Schema::hasColumn(config('spondonit.settings_table'), $moduleName)) {
                    Illuminate\Support\Facades\Schema::table(config('spondonit.settings_table'), function () use ($moduleName) { /* closure body unavailable */ });
                }
                $config = (new $settingsModelClass())->find(1);
                if ($config) {
                    $config->{$moduleName} = 0;
                    $config->save();
                }
            }
        }
        $moduleModelClass = config('spondonit.module_model');
        if ($moduleModelClass) {
            $module = $moduleModelClass::find($moduleName);
            /* [opcode 71] ZEND_JMP_NULL op1=IS_CV:144 result=IS_VAR:656 */
            $module->disable();
        }
        $this->lifecycle->afterModuleDisable($moduleName);
    }

    public function revokeModule(array $params): array {
        if (!config('spondonit.features.modules', false)) {
            return ['status' => false, 'message' => 'Modules are not enabled.'];
        }
        $name = $params['name'] ?? '';
        $response = $this->revokeAddon('module', $params);
        if (!empty($response['status'])) {
            $this->disableModule($name, !empty($params['row']), !empty($params[null]));
            $this->lifecycle->afterModuleRevoke($name);
        }
        return $response;
    }

    public function installTheme(array $params) {
        if (!config('spondonit.features.themes', false)) {
            return false;
        }
        $code = $params['purchase_code'] ?? null;
        $name = $params['name'] ?? null;
        $email = $params['envatouser'] ?? null;
        $themeTable = config('spondonit.theme_table', 'themes');
        $query = Illuminate\Support\Facades\DB::table($themeTable)->where('name', $name);
        $theme = $query->first();
        if (!$theme) {
            throw Illuminate\Validation\ValidationException::withMessages(['message' => 'Theme not found']);
        }
        $itemId = $theme->item_code;
        $url = baseUrl() . '/api/cc?a=install' . '&u=' . appUrl() . '&ac=' . $code . '&i=' . $itemId . '&e=' . $email . '&t=Theme' . '&enc=1';
        $response = connectToServer($url);
        $status = !empty($response['status']);
        if ($status) {
            $query->update([
                'email' => $email,
                'installed_domain' => appUrl(),
                'activated_date' => date('Y-m-d'),
                'purchase_code' => $code,
                'checksum' => $response['checksum'] ?? null,
            ]);
            $this->lifecycle->afterThemeInstall($name, $params, $response);
            return $response;
        }
        throw Illuminate\Validation\ValidationException::withMessages(['message' => $response['message'] ?? 'Something is not right']);
        return null;
    }

    public function revokeTheme(array $params): array {
        if (!config('spondonit.features.themes', false)) {
            return ['status' => false, 'message' => 'Themes are not enabled.'];
        }
        $name = $params['name'] ?? '';
        $response = $this->revokeAddon('theme', $params);
        if (!empty($response['status'])) {
            $themeTable = config('spondonit.theme_table', 'themes');
            Illuminate\Support\Facades\DB::table($themeTable)->where('name', $name)->update(['purchase_code' => null, 'checksum' => null]);
            $this->lifecycle->afterThemeRevoke($name);
        }
        return $response;
    }

    protected function revokeAddon(string $type, array $params): array {
        if (!isConnected()) {
            throw Illuminate\Validation\ValidationException::withMessages(['message' => 'No internet connection.']);
        }
        $name = gv($params, 'name');
        $e = Illuminate\Support\Facades\Storage::exists('.account_email') ? Illuminate\Support\Facades\Storage::get('.account_email') : null;
        $module_class_name = config('spondonit.module_manager_model');
        $moduel_class = new $module_class_name();
        $s = $moduel_class->where('name', $name)->first();
        if ($s) {
            $c = $s->checksum;
            $dataPath = base_path('Modules/' . $name . '/' . $name . '.json');
            $strJsonFileContents = file_get_contents($dataPath);
            $array = json_decode($strJsonFileContents, true);
            $item_id = config('spondonit.modules.' . $name);
            $version = $array[$name]['versions'][0];
            if (!$s->purchase_code) {
                Illuminate\Support\Facades\Log::info('Module purchase code not found');
            }
            $url = baseUrl() . '/api/cc?a=remove' . '&u=' . appUrl() . '&ac=' . $s->purchase_code . '&i=' . $item_id . '&e=' . $e . '&c=' . $c . '&t=' . 'Module' . '&v=' . $version;
            $response = connectToServer($url);
        }
        if (!empty($response['status'])) {
            $folder = storage_path('app/private/' . config('app.item'));
            $code = $params['name'] ?? '';
            if ($code && Illuminate\Support\Facades\File::exists($folder . '/' . '.' . $code)) {
                Illuminate\Support\Facades\File::delete($folder . '/' . '.' . $code);
            }
            Illuminate\Support\Facades\Log::info('Revoked ' . $type . ' license: ' . $code);
        }
        return $response;
    }
}
