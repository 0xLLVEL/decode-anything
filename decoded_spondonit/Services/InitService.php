<?php

namespace SpondonIt\Service\Services;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Services\InitService.php
 */

if (class_exists('SpondonIt\\Service\\Repositories\\InitRepository')) {
    $url = defined('INFIX_APP_URL') ? INFIX_APP_URL : 'https://codecanyon.net/item/infixlms-learning-management-system/30626608';
    $app_name = defined('INFIX_APP') ? INFIX_APP : 'CodeThemes - Portfolio';
    exit('You are using a deprecated application. Please update your code to use the application or contact the script author for more information. </br> Please visit <a href="' . $url . '">' . $app_name . ' </a> to purchase a license');
}

class InitService {
    public function __construct() {
        config([
            'app.verify_url' => config('spondonit.verify_url'),
            'app.signature' => config('spondonit.signature'),
        ]);
    }

    public function dailyCheck() {
        if (isDemoMode()) {
            return null;
        }
        if (Illuminate\Support\Facades\Storage::exists('.access_log') && Illuminate\Support\Facades\Storage::get('.access_log') === date('Y-m-d')) {
            return null;
        }
        if (!isConnected()) {
            return null;
        }
        $ac = Illuminate\Support\Facades\Storage::exists('.access_code') ? Illuminate\Support\Facades\Storage::get('.access_code') : null;
        $e = Illuminate\Support\Facades\Storage::exists('.account_email') ? Illuminate\Support\Facades\Storage::get('.account_email') : null;
        $c = Illuminate\Support\Facades\Storage::exists('.app_installed') ? Illuminate\Support\Facades\Storage::get('.app_installed') : null;
        $v = Illuminate\Support\Facades\Storage::exists('.version') ? Illuminate\Support\Facades\Storage::get('.version') : null;
        if (!$ac) {
            Illuminate\Support\Facades\Log::info('Activation code not found from init');
            return false;
        }
        $ve = Illuminate\Support\Facades\Storage::exists('.ve') ? Illuminate\Support\Facades\Storage::get('.ve') : 'e';
        $url = baseUrl() . '/api/cc?a=verify' . '&u=' . appUrl() . '&ac=' . $ac . '&i=' . config('app.item') . '&e=' . $e . '&c=' . $c . '&v=' . $v . '&current=' . urlencode(request()->path()) . '&ve=' . $ve;
        $response = connectToServer($url);
        $goto = $response['goto'] ?? null;
        if ($goto) {
            return redirect($goto)->send();
        }
        if ($response) {
            $status = !empty($response['status']);
            if (!$status) {
                Illuminate\Support\Facades\Log::info('Initial License Verification failed. Message: ' . ($response['message'] ?? ''));
                Illuminate\Support\Facades\Storage::delete(['.access_code', '.account_email']);
                Illuminate\Support\Facades\Storage::deleteDirectory(config('app.item'));
                Illuminate\Support\Facades\Storage::put('.app_installed', '');
                Illuminate\Support\Facades\Auth::logout();
                return redirect()->route('service.install')->send();
            }
        }
        Illuminate\Support\Facades\Storage::put('.access_log', date('Y-m-d'));
        return null;
    }

    public function dailyApiCheck(): bool {
        $ac = Illuminate\Support\Facades\Storage::exists('.access_code') ? Illuminate\Support\Facades\Storage::get('.access_code') : null;
        $e = Illuminate\Support\Facades\Storage::exists('.account_email') ? Illuminate\Support\Facades\Storage::get('.account_email') : null;
        $c = Illuminate\Support\Facades\Storage::exists('.app_installed') ? Illuminate\Support\Facades\Storage::get('.app_installed') : null;
        $v = Illuminate\Support\Facades\Storage::exists('.version') ? Illuminate\Support\Facades\Storage::get('.version') : null;
        if (!$ac) {
            Illuminate\Support\Facades\Log::info('Activation code not found from api check');
            return false;
        }
        $ve = Illuminate\Support\Facades\Storage::exists('.ve') ? Illuminate\Support\Facades\Storage::get('.ve') : 'e';
        $url = baseUrl() . '/api/cc?a=verify' . '&u=' . appUrl() . '&ac=' . $ac . '&i=' . config('app.item') . '&e=' . $e . '&c=' . $c . '&v=' . $v . '&ve=' . $ve;
        $response = connectToServer($url);
        if ($response && isset($response['status'])) {
            $status = !empty($response['status']);
            if (!$status) {
                Illuminate\Support\Facades\Log::info('Api License Verification failed. Message: ' . ($response['message'] ?? ''));
                return false;
            }
            return true;
        }
        return true;
    }
}
