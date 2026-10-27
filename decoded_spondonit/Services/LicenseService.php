<?php

namespace SpondonIt\Service\Services;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Services\LicenseService.php
 */

if (class_exists('SpondonIt\\Service\\Repositories\\LicenseRepository')) {
    $url = defined('INFIX_APP_URL') ? INFIX_APP_URL : 'https://codecanyon.net/item/infixlms-learning-management-system/30626608';
    $app_name = defined('INFIX_APP') ? INFIX_APP : 'CodeThemes - Portfolio';
    exit('You are using a deprecated application. Please update your code to use the application or contact the script author for more information. </br> Please visit <a href="' . $url . '">' . $app_name . ' </a> to purchase a license');
}

class LicenseService {
    public function revoke(): void {
        $ac = Illuminate\Support\Facades\Storage::exists('.access_code') ? Illuminate\Support\Facades\Storage::get('.access_code') : null;
        $e = Illuminate\Support\Facades\Storage::exists('.account_email') ? Illuminate\Support\Facades\Storage::get('.account_email') : null;
        $c = Illuminate\Support\Facades\Storage::exists('.app_installed') ? Illuminate\Support\Facades\Storage::get('.app_installed') : null;
        $v = Illuminate\Support\Facades\Storage::exists('.version') ? Illuminate\Support\Facades\Storage::get('.version') : null;
        $url = baseUrl() . '/api/cc?a=remove' . '&u=' . appUrl() . '&ac=' . $ac . '&i=' . config('app.item') . '&e=' . $e . '&c=' . $c . '&v=' . $v;
        $response = connectToServer($url);
        Illuminate\Support\Facades\Log::info($response);
        Illuminate\Support\Facades\Auth::logout();
        Illuminate\Support\Facades\Artisan::call('db:wipe', ['--force' => true]);
        $dbConnection = config('spondonit.support_multi_connection', false) ? config('database.default', null) : null;
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
        $goto = $response['goto'] ?? null;
        if ($goto) {
            redirect($goto)->send();
        }
    }
}
