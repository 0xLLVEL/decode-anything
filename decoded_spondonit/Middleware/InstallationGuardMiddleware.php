<?php

namespace SpondonIt\Service\Middleware;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Middleware\InstallationGuardMiddleware.php
 */

class InstallationGuardMiddleware {
    protected $initializer;
    protected $except = ['install', 'install/*', 'api/service/*'];

    public function __construct($initializer) {
        $this->initializer = $initializer;
    }

    public function handle($request, $next) {
        $this->initializer->init();
        if ($this->isExcluded($request)) {
            return $next($request);
        }
        $isInstalled = Illuminate\Support\Facades\Storage::exists('.app_installed') && Illuminate\Support\Facades\Storage::get('.app_installed');
        if (!$isInstalled) {
            if ($request->expectsJson()) {
                return response()->json(['message' => 'Application is not installed.'], 503);
            }
            return redirect('/install');
        }
        $this->initializer->config();
        return $next($request);
    }

    protected function isExcluded($request): bool {
        foreach ($this->except as $pattern) {
            if ($pattern !== '/') {
                $pattern = trim($pattern, '/');
            }
            if ($request->fullUrlIs($pattern) || $request->is($pattern)) {
                return true;
            }
        }
        return false;
    }
}
