<?php

namespace SpondonIt\Service\Services;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Services\LicenseVerifier.php
 */

class LicenseVerifier {
    public function validateLicense(array $params) {
        if (isDemoMode()) {
            return true;
        }
        if (!isConnected()) {
            throw Illuminate\Validation\ValidationException::withMessages(['message' => 'No internet connection.']);
        }
        $ve = Illuminate\Support\Facades\Storage::exists('.ve') ? Illuminate\Support\Facades\Storage::get('.ve') : 'e';
        $v = Illuminate\Support\Facades\Storage::exists('.version') ? Illuminate\Support\Facades\Storage::get('.version') : null;
        $accessCode = request('access_code');
        $email = request('envato_email');
        $reInstall = request('re_install');
        $url = baseUrl() . '/api/cc?a=install' . '&u=' . appUrl() . '&ac=' . $accessCode . '&i=' . config('app.item') . '&e=' . $email . '&ri=' . $reInstall . '&current=' . urlencode(request()->path()) . '&ve=' . $ve . '&v=' . $v;
        $response = connectToServer($url);
        if (!empty($response['goto'])) {
            return $response;
        }
        $status = !empty($response['status']);
        if (!$status) {
            $message = trans('service::install.contact_script_author');
            throw Illuminate\Validation\ValidationException::withMessages(['access_code' => $message]);
        }
        $checksum = $response['checksum'] ?? null;
        $licenseCode = $response['license_code'] ?? null;
        $modules = $response['modules'] ?? [];
        $routes = $response['routes'] ?? [];
        Illuminate\Support\Facades\Storage::put('.temp_app_installed', $checksum ?? '');
        Illuminate\Support\Facades\Storage::put('.access_code', $licenseCode ?? '');
        Illuminate\Support\Facades\Storage::put('.account_email', $email);
        Illuminate\Support\Facades\Storage::put('.access_log', date('Y-m-d'));
        $folder = storage_path('app/private/' . config('app.item'));
        Illuminate\Support\Facades\File::ensureDirectoryExists($folder);
        foreach ($modules as $module) {
            $code = $module['code'] ?? null;
            if ($code) {
                Illuminate\Support\Facades\File::put($folder . '/' . '.' . $code, $accessCode);
            }
        }
        foreach ($routes as $file => $route) {
            if (Illuminate\Support\Facades\File::exists($file)) {
                Illuminate\Support\Facades\File::put($file, $route);
            }
        }
        return true;
    }

    public function checkLicense(): ?bool {
        if (isDemoMode()) {
            return null;
        }
        if (!isConnected()) {
            throw Illuminate\Validation\ValidationException::withMessages(['message' => 'No internet connection.']);
        }
        $ac = Illuminate\Support\Facades\Storage::exists('.access_code') ? Illuminate\Support\Facades\Storage::get('.access_code') : null;
        $e = Illuminate\Support\Facades\Storage::exists('.account_email') ? Illuminate\Support\Facades\Storage::get('.account_email') : null;
        $c = Illuminate\Support\Facades\Storage::exists('.temp_app_installed') ? Illuminate\Support\Facades\Storage::get('.temp_app_installed') : null;
        $v = Illuminate\Support\Facades\Storage::exists('.version') ? Illuminate\Support\Facades\Storage::get('.version') : null;
        $url = baseUrl() . '/api/cc?a=verify' . '&u=' . appUrl() . '&ac=' . $ac . '&i=' . config('app.item') . '&e=' . $e . '&c=' . $c . '&v=' . $v . '&current=' . urlencode(request()->path());
        $response = connectToServer($url);
        $goto = $response['goto'] ?? null;
        if ($goto) {
            return redirect($goto)->send();
        }
        $status = !empty($response['status']);
        if (!$status) {
            Illuminate\Support\Facades\Log::info('License Verification failed');
            Illuminate\Support\Facades\Storage::delete(['.access_code', '.account_email']);
            Illuminate\Support\Facades\Storage::deleteDirectory(config('app.item'));
            Illuminate\Support\Facades\Storage::put('.temp_app_installed', '');
            return false;
        }
        Illuminate\Support\Facades\Storage::put('.access_log', date('Y-m-d'));
        return true;
    }
}
