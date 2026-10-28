<?php

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;

if (!function_exists('isDemoMode')) {
    function isDemoMode(): bool {
        return (bool) (config('app.app_sync') || config('app.demo_mode'));
    }
}
if (!function_exists('updateEnvFile')) {
    function updateEnvFile(array $data = []): bool {
        foreach ($data as $key => $value) {
            if (env($key) === $value) {
                unset($data[$key]);
            }
        }
        if (count($data) === 0) {
            return false;
        }
        $env = file_get_contents(base_path('.env'));
        $env = explode("\n", $env);
        foreach ($data as $key => $value) {
            $found = false;
            foreach ($env as $envKey => $envValue) {
                $entry = explode('=', $envValue, 2);
                if ($entry[0] === $key) {
                    $env[$envKey] = $key . '=' . (is_string($value) ? '"' . $value . '"' : $value);
                    $found = true;
                }
            }
            if (!$found) {
                $env[] = $key . '=' . (is_string($value) ? '"' . $value . '"' : $value);
            }
        }
        $env = implode("\n", $env);
        file_put_contents(base_path('.env'), $env);
        return true;
    }
}
if (!function_exists('envu')) {
    function envu(array $data = []): bool {
        return updateEnvFile($data);
    }
}
if (!function_exists('isConnected')) {
    function isConnected(): bool {
        $connected = @fsockopen('google.com', 80);
        if ($connected) {
            fclose($connected);
            return true;
        }
        return false;
    }
}
if (!function_exists('connectToServer')) {
    function connectToServer(string $url, array $postData = []): array {
        $url = preg_replace("/\r|\n/", '', $url);
        $url .= '&encoder=ioncube';
        $response = Http::timeout(15)->acceptJson()->get($url);
        if ($response->successful()) {
            return $response->json() ?? [];
        }
        try {
            return [];
        } catch (\Exception $e) {
            Log::error($e);
        }
        return ['goto' => $url . '&from=browser'];
    }
}
if (!function_exists('appUrl')) {
    function appUrl(): string {
        $saas = config('spondonit.saas_module_name', 'Saas');
        $checkFn = config('spondonit.module_status_check_function', 'moduleStatusCheck');
        if (function_exists($checkFn) && $checkFn($saas)) {
            return config('app.url');
        }
        return url('/');
    }
}
if (!function_exists('app_url')) {
    function app_url(): string {
        return appUrl();
    }
}
if (!function_exists('baseUrl')) {
    function baseUrl(?string $verifier = null): string {
        return config('app.verify_url', config('spondonit.verify_url'));
    }
}
if (!function_exists('isInstalled')) {
    function isInstalled(): bool {
        return (bool) (Storage::exists('.app_installed') && Storage::get('.app_installed'));
    }
}
if (!function_exists('gv')) {
    function gv($params, string $key, $default = null) {
        return isset($params[$key]) && $params[$key] ? $params[$key] : $default;
    }
}
if (!function_exists('gbv')) {
    function gbv($params, string $key): bool {
        return isset($params[$key]) && $params[$key];
    }
}
if (!function_exists('active_progress_bar')) {
    function active_progress_bar(array $routeOrPathArr, string $class = 'active') {
        /* [opcode 7] ZEND_JMP_NULL op1=IS_VAR:96 result=IS_VAR:112 */
        return in_array(request()->route()->getName(), $routeOrPathArr, false) ? $class : false;
    }
}
if (!function_exists('active_link')) {
    function active_link(string $routeOrPath, string $class = 'active') {
        /* [opcode 6] ZEND_JMP_NULL op1=IS_VAR:96 result=IS_VAR:112 */
        if (request()->route()->getName() === $routeOrPath) {
            return $class;
        }
        if (request()->is($routeOrPath)) {
            return $class;
        }
        return false;
    }
}
