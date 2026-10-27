<?php

namespace SpondonIt\Service\Controllers;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Controllers\VerifyController.php
 */

class VerifyController extends Illuminate\Routing\Controller {
    protected $request;

    public function __construct($request) {
        $this->request = $request;
    }

    public function index() {
        $requests = $this->request->all();
        $response = $requests['response'] ?? [];
        $params = $requests['params'] ?? [];
        if (!empty($response['status'])) {
            return $this->successAction($requests, $response, $params);
        }
        if (($params['a'] ?? null) === 'verify') {
            Illuminate\Support\Facades\Log::info('Initial License Verification failed. Message: ' . ($response['message'] ?? ''));
            Illuminate\Support\Facades\Storage::delete(['.access_code', '.account_email']);
            Illuminate\Support\Facades\Storage::deleteDirectory(config('app.item'));
            Illuminate\Support\Facades\Storage::put('.app_installed', '');
            Illuminate\Support\Facades\Storage::put('.logout', 'true');
            Illuminate\Support\Facades\Auth::logout();
            $goto = route('service.install');
            if (($requests['from'] ?? null) === 'browser') {
                return redirect($goto)->send();
            }
            return ['status' => false, 'goto' => $goto];
        }
        try {
            return $response;
        } catch (\Exception $e) {
            Illuminate\Support\Facades\Log::error($e);
            $goto = url('login');
            if (($params['a'] ?? null) === 'verify') {
            Illuminate\Support\Facades\Storage::put('.access_log', date('Y-m-d'));
            }
            if (!$goto) {
            $goto = route('service.install');
            }
            if (($requests['from'] ?? null) === 'browser') {
            session()->flash('message', $e->getMessage());
            session()->flash('status', 'error');
            return redirect($goto)->send();
            }
            return ['status' => false, 'goto' => $goto, 'message' => $e->getMessage()];
        }
    }

    public function successAction(array $requests, array $response, array $params) {
        $action = $params['a'] ?? null;
        if ($action === 'install') {
            $checksum = $response['checksum'] ?? null;
            $licenseCode = $response['license_code'] ?? null;
            if (!empty($params['ri'])) {
                Illuminate\Support\Facades\Storage::put('.app_installed', $checksum ?? '');
                Illuminate\Support\Facades\Storage::put('.install_count', (int) Illuminate\Support\Facades\Storage::get('.install_count') + 1);
                $goto = url('/');
                $message = __('service::install.re_installation_process_complete');
            } else {
                Illuminate\Support\Facades\Storage::put('.temp_app_installed', $checksum ?? '');
                $goto = route('service.database');
                $message = __('service::install.valid_license');
            }
            Illuminate\Support\Facades\Storage::put('.access_code', $licenseCode ?? '');
            Illuminate\Support\Facades\Storage::put('.account_email', $params['e'] ?? '');
            Illuminate\Support\Facades\Storage::put('.access_log', date('Y-m-d'));
            session()->flash('message', $message);
            session()->flash('status', 'success');
        } elseif ($action === 'verify') {
            Illuminate\Support\Facades\Storage::put('.access_log', date('Y-m-d'));
            $goto = url('dashboard');
        } else {
            $goto = url('/');
        }
        if (($requests['from'] ?? null) === 'browser') {
            return redirect($goto);
        }
        return ['status' => true, 'goto' => $goto];
    }
}
