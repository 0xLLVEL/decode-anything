<?php

namespace SpondonIt\Service\Services;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Services\PreRequisiteChecker.php
 */

class PreRequisiteChecker {
    public function getPreRequisite(): array {
        $server = $this->getServerChecks();
        $server = array_merge($server, $this->getAppPreRequisiteChecks());
        $folder = $this->getFolderChecks();
        return [
            'server' => $server,
            'folder' => $folder,
            'verifier' => baseUrl(),
        ];
        return null;
    }

    protected function getServerChecks(): array {
        $checks = [];
        $checks[] = $this->checkInstallDirectory();
        $checks[] = $this->checkPhpVersion();
        $checks = array_merge($checks, $this->checkRequiredExtensions());
        $checks[] = $this->check((bool) ini_get('allow_url_fopen'), 'allow_url_fopen is on.', 'Turn on allow_url_fopen.', true);
        $checks = array_merge($checks, $this->checkIniSettings());
        return $checks;
    }

    protected function checkInstallDirectory(): array {
        $dir = dirname($_SERVER['REQUEST_URI']);
        $isValid = $dir != '/' && str_replace('\\', '/', $dir) != '/';
        return $this->check($isValid, 'Installation directory is valid.', 'Please use root directory or point your sub directory to domain/subdomain to install.', true);
    }

    protected function checkPhpVersion(): array {
        $minVersion = config('spondonit.php_version', '8.2.0');
        return $this->check(version_compare(phpversion(), $minVersion, '>='), 'Current Version ' . phpversion(), sprintf('Min PHP version ' . $minVersion . ' (%s)', 'Current PHP Version ' . phpversion()), true);
    }

    protected function checkRequiredExtensions(): array {
        $extensions = [
            ['extension' => 'fileinfo', 'label' => 'Fileinfo'],
            ['extension' => 'ctype', 'label' => 'Ctype'],
            ['extension' => 'json', 'label' => 'JSON'],
            ['extension' => 'openssl', 'label' => 'OpenSSL'],
            ['extension' => 'tokenizer', 'label' => 'Tokenizer'],
            ['extension' => 'mbstring', 'label' => 'Mbstring'],
            ['extension' => 'zip', 'label' => 'Zip archive'],
            ['extension' => 'curl', 'label' => 'CURL'],
        ];
        $classes = [
            [
                'class' => 'finfo',
                'label' => 'Finfo',
                'help' => 'Install Finfo (mandatory for read or write file).',
            ],
            [
                'class' => 'PDO',
                'label' => 'PDO',
                'help' => 'Install PDO (mandatory for Eloquent).',
            ],
        ];
        $checks = [];
        foreach ($extensions as $ext) {
            $checks[] = $this->check(extension_loaded($ext['extension']), $ext['label'] . ' PHP extension enabled.', 'Install and enable ' . $ext['label'] . ' extension.', true);
        }
        foreach ($classes as $cls) {
            $checks[] = $this->check(class_exists($cls['class']), $cls['label'] . ' is installed.', $cls['help'], true);
        }
        return $checks;
    }

    protected function checkIniSettings(): array {
        $settings = [
            [
                'ini' => 'post_max_size',
                'config' => 'spondonit.post_max_size',
                'default' => '64M',
                'label' => 'Post Max Size',
            ],
            [
                'ini' => 'memory_limit',
                'config' => 'spondonit.memory_limit',
                'default' => '128M',
                'label' => 'Memory Limit',
            ],
            [
                'ini' => 'upload_max_filesize',
                'config' => 'spondonit.upload_max_filesize',
                'default' => '32M',
                'label' => 'Upload Max File Size',
            ],
            [
                'ini' => 'max_execution_time',
                'config' => 'spondonit.max_execution_time',
                'default' => 300,
                'label' => 'Max Execution time',
            ],
        ];
        $checks = [];
        foreach ($settings as $setting) {
            $requiredValue = config($setting['config'], $setting['default']);
            $currentValue = ini_get($setting['ini']);
            $requiredInt = is_numeric($requiredValue) ? (int) $requiredValue : $this->convertToInt($requiredValue);
            $checks[] = $this->check($this->compareInt($this->getIniSize($setting['ini']), $requiredInt), 'Current ' . $setting['label'] . ' ' . $currentValue, sprintf('Min ' . $setting['label'] . ' ' . $requiredValue . ' (%s)', 'Current ' . lcfirst($setting['label']) . ' ' . $currentValue), true);
        }
        return $checks;
    }

    protected function getFolderChecks(): array {
        $paths = [
            '/.env' => 'File .env',
            '/storage/app' => 'Folder /storage/app',
            '/storage/framework' => 'Folder /storage/framework',
            '/storage/logs' => 'Folder /storage/logs',
            '/bootstrap/cache' => 'Folder /bootstrap/cache',
        ];
        $checks = [];
        foreach ($paths as $path => $label) {
            $checks[] = $this->check(is_writable(base_path($path)), $label . ' is writable', $label . ' is not writable', true);
        }
        return $checks;
    }

    protected function getAppPreRequisiteChecks(): array {
        $preRequisite = config('spondonit.pre_requisite', []);
        if (!is_array($preRequisite) || empty($preRequisite)) {
            return [];
        }
        $checks = [];
        foreach ($preRequisite as $item) {
            if (!is_array($item) || !(isset($item['type']) && isset($item['message']) && isset($item['help']) && isset($item['fatal']))) {
                continue;
            }
            $checks[] = $this->check($item['type'], $item['message'], $item['help'], (bool) $item['fatal']);
        }
        return $checks;
    }

    public function check(bool $boolean, string $message, string $help = '', bool $fatal = false): array {
        if ($boolean) {
            return ['type' => 'success', 'message' => $message];
        }
        return ['type' => 'error', 'message' => $help];
    }

    protected function getIniSize(string $var) {
        $size = ini_get($var);
        if (is_numeric($size)) {
            return (int) $size;
        }
        return $this->convertToInt($size);
    }

    protected function compareInt($int1, $int2): bool {
        if ($int1 < 0) {
            return true;
        }
        return $int2 <= $int1;
    }

    protected function convertToInt(string $size) {
        $metric = strtoupper(substr($size, -1));
        $numericSize = (int) $size;
        return match ($metric) {
            'K' => $numericSize * 1024,
            'M' => $numericSize * 1048576,
            'G' => $numericSize * 1073741824,
            default => $numericSize,
        };
    }
}
