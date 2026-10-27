<?php

namespace SpondonIt\Service\Controllers;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Controllers\SpondonController.php
 */

class SpondonController extends Illuminate\Routing\Controller {
    protected $repo;
    protected $installer;
    protected $request;

    public function __construct($repo, $installer, $request) {
        $this->repo = $repo;
        $this->installer = $installer;
        $this->request = $request;
    }

    public function index() {
        $this->repo->checkInstallation();
        return view('service::install.welcome');
    }

    public function user() {
        if (!$this->repo->checkDatabaseConnection()) {
            abort(404);
        }
        return view('service::install.user');
    }

    public function postUser($request) {
        $params = $request->all();
        session()->put('service.install.user', $params['email'] ?? null);
        session()->put('service.install.pass', $params['password'] ?? null);
        Illuminate\Support\Facades\Storage::put('.install_status', 'processing');
        Illuminate\Support\Facades\Storage::delete('.install_error');
        app()->terminating(function () use ($params) { /* closure body unavailable */ });
        $payload = [
            'message' => __('We are installing your system. Please wait while the setup finishes.'),
            'goto' => route('service.processing'),
        ];
        if ($request->expectsJson()) {
            return response()->json($payload);
        }
        return redirect()->route('service.processing');
    }

    public function processing() {
        $status = Illuminate\Support\Facades\Storage::exists('.install_status') ? Illuminate\Support\Facades\Storage::get('.install_status') : null;
        if ($status === 'done') {
            return redirect()->route('service.done');
        }
        if ($status === 'failed') {
            return redirect()->route('service.user')->with([
                'message' => Illuminate\Support\Facades\Storage::exists('.install_error') ? Illuminate\Support\Facades\Storage::get('.install_error') : __('service::install.installation_failed'),
                'status' => 'error',
            ]);
        }
        if (view()->exists('service::install.processing')) {
            return view('service::install.processing');
        }
        $statusUrl = route('service.install.status');
        $doneUrl = route('service.done');
        $userUrl = route('service.user');
        $csrf = csrf_token();
        $title = config('spondonit.branding.admin_setup_title', __('service::install.admin_setup'));
        $message = __('We are installing your system. Please wait while the setup finishes.');
        $hint = __('Do not refresh or close this window until the setup is complete.');
        $html = '<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="csrf-token" content="' . e($csrf) . '">' . '<title>' . e($title) . '</title>' . '<link rel="stylesheet" href="' . e(asset(config('spondonit.branding.asset_path', 'vendor/spondonit') . '/css/installer.css')) . '">' . '</head><body>' . '<div class="installer-wrapper"><div class="installer-container"><div class="card">' . '<div class="card-header"><h2>' . e($title) . '</h2></div>' . '<div class="card-body text-center">' . '<div class="hero-icon success"><div class="spinner"></div></div>' . '<p class="text-secondary" id="install-status-message">' . e($message) . '</p>' . '<p class="form-hint" id="install-status-hint">' . e($hint) . '</p>' . '</div></div></div></div>' . '<script>var statusUrl=' . json_encode($statusUrl) . ';var doneUrl=' . json_encode($doneUrl) . ';var userUrl=' . json_encode($userUrl) . ';var messageEl=document.getElementById("install-status-message");var hintEl=document.getElementById("install-status-hint");(function poll(){fetch(statusUrl,{headers:{Accept:"application/json"}}).then(function(r){return r.json()}).then(function(data){if(data.status==="done"){window.location.href=data.goto||doneUrl;return;}if(data.status==="failed"){if(messageEl){messageEl.textContent=data.message||"Installation failed.";}if(hintEl){hintEl.textContent="";var a=document.createElement("a");a.href=userUrl;a.textContent="Try again";hintEl.appendChild(a);}return;}setTimeout(poll,2000);}).catch(function(){setTimeout(poll,3000);});})();</script>' . '</body></html>';
        return response($html);
    }

    public function installStatus() {
        $status = Illuminate\Support\Facades\Storage::exists('.install_status') ? Illuminate\Support\Facades\Storage::get('.install_status') : 'processing';
        return response()->json([
            'status' => $status,
            'goto' => $status === 'done' ? route('service.done') : null,
            'message' => $status === 'failed' && Illuminate\Support\Facades\Storage::exists('.install_error') ? Illuminate\Support\Facades\Storage::get('.install_error') : null,
        ]);
    }

    public function getPreRequisite() {
        $ac = Illuminate\Support\Facades\Storage::exists('.app_installed') ? Illuminate\Support\Facades\Storage::get('.app_installed') : null;
        if ($ac) {
            abort(404);
        }
        $checks = $this->repo->getPreRequisite();
        $server_checks = $checks['server'];
        $folder_checks = $checks['folder'];
        $verifier = $checks['verifier'];
        $has_false = in_array(false, $checks);
        updateEnvFile(['APP_ENV' => 'production']);
        $name = config('app.name');
        return view('service::install.preRequisite', compact('server_checks', 'folder_checks', 'name', 'verifier', 'has_false'));
    }

    public function license() {
        $checks = $this->repo->getPreRequisite();
        if (in_array(false, $checks)) {
            return redirect()->route('service.preRequisite')->with([
                'message' => __('service::install.requirement_failed'),
                'status' => 'error',
            ]);
        }
        $ac = Illuminate\Support\Facades\Storage::exists('.app_installed') ? Illuminate\Support\Facades\Storage::get('.app_installed') : null;
        if ($ac) {
            abort(404);
        }
        $reinstall = $this->repo->checkReinstall();
        return view('service::install.license', compact('reinstall'));
    }

    public function postLicense($request) {
        $response = $this->repo->validateLicense($request->all());
        if ($response && is_array($response) && ($response['goto'] ?? null)) {
            $message = __('Please wait to verify the license. Thank you.');
            $goto = $response['goto'];
        } else {
            session()->flash('license', 'verified');
            $goto = route('service.database');
            $message = __('service::install.valid_license');
            if (request('re_install') && $this->repo->checkReinstall()) {
                Illuminate\Support\Facades\Storage::put('.app_installed', Illuminate\Support\Facades\Storage::get('.temp_app_installed'));
                Illuminate\Support\Facades\Storage::delete('.temp_app_installed');
                Illuminate\Support\Facades\Storage::put('.install_count', (int) Illuminate\Support\Facades\Storage::get('.install_count') + 1);
                $goto = url('/');
                $message = __('service::install.re_installation_process_complete');
            }
        }
        return response()->json(['message' => $message, 'goto' => $goto]);
    }

    public function database() {
        $ac = Illuminate\Support\Facades\Storage::exists('.temp_app_installed') ? Illuminate\Support\Facades\Storage::get('.temp_app_installed') : null;
        if (!$ac) {
            abort(404);
        }
        if ($this->repo->checkDatabaseConnection()) {
            return redirect()->route('service.user')->with([
                'message' => __('service::install.connection_established'),
                'status' => 'success',
            ]);
        }
        return view('service::install.database');
    }

    public function postDatabase($request) {
        $this->repo->validateDatabase($request->all());
        return response()->json([
            'message' => __('service::install.connection_established'),
            'goto' => route('service.user'),
        ]);
    }

    public function done() {
        $data['user'] = Illuminate\Support\Facades\Storage::exists('.user_email') ? Illuminate\Support\Facades\Storage::get('.user_email') : session('service.install.user');
        $data['pass'] = Illuminate\Support\Facades\Storage::exists('.user_pass') ? Illuminate\Support\Facades\Storage::get('.user_pass') : session('service.install.pass');
        if ($data['user'] && $data['pass']) {
            Illuminate\Support\Facades\Log::info('done');
            Illuminate\Support\Facades\Storage::delete(['.user_email', '.user_pass']);
            Illuminate\Support\Facades\Storage::put('.install_count', 1);
            session()->forget(['service.install.user', 'service.install.pass']);
            return view('service::install.done', $data);
        }
        abort(404);
    }

    public function revokeLicense() {
        $response = $this->repo->uninstall($this->request->all());
        $message = 'Uninstall by script author successfully';
        info($message);
        return response()->json(['message' => $message, 'response' => $response]);
    }
}
