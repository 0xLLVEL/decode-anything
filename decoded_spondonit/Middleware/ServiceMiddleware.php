<?php

namespace SpondonIt\Service\Middleware;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Middleware\ServiceMiddleware.php
 */

class ServiceMiddleware {
    protected $initService;

    public function __construct($initService) {
        $this->initService = $initService;
    }

    public function handle($request, $next) {
        if (!isInstalled()) {
            return $next($request);
        }
        $logout = Illuminate\Support\Facades\Storage::exists('.logout') && Illuminate\Support\Facades\Storage::get('.logout');
        if ($logout) {
            $request->session()->flush();
            Illuminate\Support\Facades\Storage::delete('.logout');
            return redirect('/install');
        }
        if (Illuminate\Support\Facades\Auth::check()) {
            $this->initService->dailyCheck();
        }
        return $next($request);
    }
}
