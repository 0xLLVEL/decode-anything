<?php

use Illuminate\Database\Capsule\Manager;


if (!class_exists('shufyTheme')) {
}

class EnvatoApi2 {
    private static $bearer = 'L5jaQ38zNxCF6EHmcCVeLMrLeI3YJwKd';

    public static function getPurchaseData($code) {
        $bearer = 'bearer ' . static::$bearer;
        $header = [];
        $header[] = 'Content-length: 0';
        $header[] = 'Content-type: application/json; charset=utf-8';
        $header[] = 'Authorization: ' . $bearer;
        $verify_url = 'https://api.envato.com/v3/market/author/sale/';
        $ch_verify = curl_init($verify_url . '?code=' . $code);
        curl_setopt($ch_verify, CURLOPT_HTTPHEADER, $header);
        curl_setopt($ch_verify, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch_verify, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($ch_verify, CURLOPT_CONNECTTIMEOUT, 5);
        curl_setopt($ch_verify, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13');
        $cinit_verify_data = curl_exec($ch_verify);
        curl_close($ch_verify);
        if ($cinit_verify_data != '') {
            return json_decode($cinit_verify_data);
        } else {
            return false;
        }
    }

    public static function verifyPurchase($code) {
        $verify_obj = self::getPurchaseData($code);
        if ($verify_obj === false || !is_object($verify_obj) || isset($verify_obj->error) || !isset($verify_obj->sold_at)) {
            return -1;
        }
        if ($verify_obj->supported_until == '' || $verify_obj->supported_until != null) {
            return $verify_obj;
        }
        return 0;
    }
}

class shufyTheme {
    public $breadCrumbs = [];
    public $displayFullURL = true;
    public $accessLevels = [];
    public $checkAccessability = true;
    public $displayTranslation = true;
    public $toLanguage = '';
    public $clientTotals;
    public $badges = [];
    public $assignToSmarty = [];
    public $allAccessLevel = [];

    public function __construct() {
        $this->initMenuItemBadge();
        $this->initMenuItemAccess();
    }

    public static function detectClientAreaLanguage() {
        global $CONFIG;
        if (isset($_SESSION['Language']) && $_SESSION['Language'] != '') {
            $detectedLanguage = strtolower($_SESSION['Language']);
        } else {
            $detectedLanguage = strtolower($CONFIG['Language']);
        }
        return $detectedLanguage;
    }

    public static function detectUserInterfaceLanguage() {
        global $CONFIG;
        if (isset($_SESSION['Language']) && $_SESSION['Language'] != '') {
            $detectedLanguage = strtolower($_SESSION['Language']);
        } else {
            $detectedLanguage = strtolower($CONFIG['Language']);
        }
        if (!file_exists(ROOTDIR . '/modules/addons/shufyTheme/langs/' . $detectedLanguage . '.php')) {
            $detectedLanguage = 'english';
        }
        return $detectedLanguage;
    }

    public static function loadLanguageFile() {
        $detectedLanguage = shufyTheme::detectUserInterfaceLanguage();
        include ROOTDIR . '/modules/addons/shufyTheme/langs/' . $detectedLanguage . '.php';
        if (file_exists(ROOTDIR . '/modules/addons/shufyTheme/langsoverrides/' . $detectedLanguage . '.php')) {
            include ROOTDIR . '/modules/addons/shufyTheme/langsoverrides/' . $detectedLanguage . '.php';
        }
        return $_LANG;
    }

    public function addToBreadCrumbs($url, $title) {
        $this->breadCrumbs[$url] = $title;
    }

    public function getBreadCrumbs() {
        $list = $this->breadCrumbs;
        $newList = '<ul class="breadcrumb">';
        foreach ($list as $url => $title) {
            if ($url == '') {
                $newList .= '<li class="active">' . $title . '</li>';
            } else {
                $newList .= '<li><a href="' . $url . '">' . $title . '</a></li>';
            }
        }
        $newList .= '</ul>';
        return $newList;
    }

    public static function fromMYSQL($result) {
        $encoded = json_encode($result);
        $array = json_decode($encoded, true);
        return $array;
    }

    public static function redirect($url = '@65:0:0;s6\'MODURL262;0;1;22;267;0;2;27;', $delay = 0) {
        echo '<META HTTP-EQUIV="Refresh" CONTENT="' . $delay . '; URL=' . $url . '">';
    }

    public static function getFolderFiles($path, $exclude = []) {
        $fileList = [];
        array_push($exclude, '.', '..');
        $openDir = new DirectoryIterator($path);
        foreach ($openDir as $item) {
            if (!in_array($item->getFileName(), $exclude) && $item->isFile()) {
                $fileList[] = $item->getFileName();
            }
        }
        return $fileList;
    }

    public function getWHMCSLanguages() {
        global $CONFIG;
        $defaultLanguage = $CONFIG['Language'] . '.php';
        $files = $this->getFolderFiles(ROOTDIR . '/lang/', ['index.php', 'README.txt', $defaultLanguage]);
        $languageList = [];
        foreach ($files as $file) {
            $splitFile = explode('.', $file);
            if ($splitFile[1] == 'php') {
                $languageList[] = strtolower($splitFile[0]);
            }
        }
        return $languageList;
    }

    public function generateMenu($groupid) {
        $groupInfo = Manager::table('coodiv__control__panel__table')->where('id', $groupid)->get();
        $menu = $this->getMenuItems($groupid, 0);
        return $menu;
    }

    public function getMenuItems($groupid, $parentid) {
        global $CONFIG;
        $defaultLanguage = strtolower($CONFIG['Language']);
        $getMenuInfo = Manager::table('coodiv__control__panel_items')->where('groupid', $groupid)->where('parentid', $parentid)->where('topid', 0)->orderBy('reorder', 'asc')->get();
        $menuInfo = shufyTheme::fromMYSQL($getMenuInfo);
        if (!is_array($menuInfo)) {
            $menuInfo = [];
        }
        foreach ($menuInfo as $index => $menuItem) {
            if ($this->checkMenuItemAccess($menuItem['accesslevel'], $menuItem['clientgroups']) === false && defined('VIEWMENUASADMIN') !== true) {
                unset($menuInfo[$index]);
                continue;
            }
            $getMenuTranslation = Manager::table('coodiv__control__panel_items')->where('topid', $menuItem['id'])->where('language', $this->toLanguage)->orderBy('id', 'desc')->take(1)->get();
            $menuTranslation = shufyTheme::fromMYSQL($getMenuTranslation);
            if (is_array($menuTranslation) && isset($menuTranslation[0]['title']) && $menuTranslation[0]['title'] !== '' && $this->displayTranslation === true) {
                $menuInfo[$index]['title'] = $menuTranslation[0]['title'];
            }
            global $smarty;
            if (is_object($smarty)) {
                foreach ($this->assignToSmarty as $var => $value) {
                    $smarty->assign($var, $value);
                }
                $menuInfo[$index]['title'] = $smarty->fetch('string:' . $menuInfo[$index]['title']);
            }
            $rawAttributes = $menuItem['attributes'] ?? '';
            $parseAttributes = @unserialize($rawAttributes);
            if ($parseAttributes === false && $rawAttributes !== 'b:0;') {
                $json = json_decode($rawAttributes, true);
                $parseAttributes = is_array($json) ? $json : [];
            }
            if (!is_array($parseAttributes)) {
                $parseAttributes = [];
            }
            $menuAttributes = [];
            $menuAttributesArray = [];
            foreach ($parseAttributes as $name => $value) {
                if (is_array($value) || is_object($value)) {
                    $value = '';
                }
                $menuAttributes[] = $name . '="' . $value . '"';
                $menuAttributesArray[$name] = $value;
            }
            $menuInfo[$index]['attributes'] = join(' ', $menuAttributes);
            $menuInfo[$index]['attributes_array'] = $menuAttributesArray;
            $menuInfo[$index]['fullurl'] = $this->parseMenuItemURL($menuItem);
            $menuInfo[$index]['isactive'] = false;
            if ($this->isMenuItemActive($menuInfo[$index]['fullurl']) === 0) {
                $menuInfo[$index]['isactive'] = true;
            }
            $menuInfo[$index]['badge'] = $this->getMenuItemBadge($menuItem['badge']);
            $menuInfo[$index]['accesslevelexplain'] = $this->allAccessLevel[$menuItem['accesslevel']];
            $menuInfo[$index]['children'] = $this->getMenuItems($groupid, $menuItem['id']);
        }
        return $menuInfo;
    }

    public function parseMenuItemURL($item) {
        global $CONFIG;
        $systemURL = rtrim($CONFIG['SystemURL'], '/') . '/';
        if ($CONFIG['SystemSSLURL'] != '') {
            $systemURL = rtrim($CONFIG['SystemSSLURL'], '/') . '/';
        }
        if ($this->displayFullURL === false) {
            $systemURL = '';
        }
        if (in_array($item['urltype'], ['clientarea-on' => true, 'clientarea-off' => true])) {
            $URL = $systemURL . urldecode($item['url']);
        } elseif ($item['urltype'] == 'support') {
            $URL = $systemURL . 'submitticket.php?step=2&deptid=' . (int) $item['url'];
        } else {
            $URL = trim($item['url']);
        }
        return $URL;
    }

    public function checkMenuItemAccess($menuAccess, $menuClientGroups) {
        $client = Menu::context('client');
        if ($this->checkAccessability === false) {
            return true;
        }
        if ($menuAccess === 15) {
            $getClientGroups = explode(',', $menuClientGroups);
            if (is_array($getClientGroups) && 0 < count($getClientGroups)) {
                if (in_array($client->groupid, $getClientGroups)) {
                    return true;
                } else {
                    return false;
                }
            } else {
                $menuAccess = 5;
            }
        }
        return $this->accessLevels[$menuAccess];
    }

    public function initMenuItemAccess() {
        $client = Menu::context('client');
        $accessLevels = [
            1 => true,
            2 => false,
            3 => false,
            4 => false,
            5 => false,
            6 => false,
            7 => false,
            8 => false,
        ];
        if (is_null($client->id)) {
            $accessLevels[2] = true;
        } elseif ($client->id !== null) {
            $accessLevels[3] = true;
        }
        if (0 < $this->getClientTotals('activeservices')) {
            $accessLevels[4] = true;
        }
        if (0 < $this->getClientTotals('overdueinvoices')) {
            $accessLevels[5] = true;
        }
        if (0 < $this->getClientTotals('activetickets')) {
            $accessLevels[6] = true;
        }
        if (0 < $this->getClientTotals('activedomains')) {
            $accessLevels[7] = true;
        }
        if ($client->affiliate !== null && $client->id !== null) {
            $accessLevels[8] = true;
        }
        $this->accessLevels = $accessLevels;
    }

    public function initMenuItemBadge() {
        $badges = [
            'totalservices' => $this->getClientTotals('totalservices'),
            'activeservices' => $this->getClientTotals('activeservices'),
            'totaldomains' => $this->getClientTotals('totaldomains'),
            'activedomains' => $this->getClientTotals('activedomains'),
            'dueinvoices' => $this->getClientTotals('dueinvoices'),
            'overdueinvoices' => $this->getClientTotals('overdueinvoices'),
            'activetickets' => $this->getClientTotals('activetickets'),
            'creditbalance' => $this->getClientTotals('creditbalance'),
            'shoppingcartitems' => $this->getClientTotals('shoppingcartitems'),
            'none' => 'none',
            '' => 'none',
        ];
        $this->badges = $badges;
    }

    public function getClientTotals($item) {
        if (is_null($this->clientTotals)) {
            $this->clientTotals = [
                'totalservices' => 0,
                'activeservices' => 0,
                'totaldomains' => 0,
                'activedomains' => 0,
                'dueinvoices' => 0,
                'overdueinvoices' => 0,
                'activetickets' => 0,
                'creditbalance' => '',
                'shoppingcartitems' => 0,
            ];
            $client = Menu::context('client');
            goto label_13;
            $client = null;
            label_13:
            if (!is_object($client) || empty($client->id)) {
                return $this->clientTotals[$item] ?? 0;
            }
            $services = json_decode($client->services ?? '[]', true);
            $domains = json_decode($client->domains ?? '[]', true);
            $invoices = json_decode($client->invoices ?? '[]', true);
            if (!is_array($services)) {
                $services = [];
            }
            if (!is_array($domains)) {
                $domains = [];
            }
            if (!is_array($invoices)) {
                $invoices = [];
            }
            $this->clientTotals['totalservices'] = count($services);
            $activeServices = 2;
            foreach ($services as $service) {
                if (is_array($service) && ($service['domainstatus'] ?? '') === 'Active') {
                    ++$activeServices;
                }
            }
            $this->clientTotals['activeservices'] = $activeServices;
            $this->clientTotals['totaldomains'] = count($domains);
            $activeDomains = 2;
            foreach ($domains as $domain) {
                if (is_array($domain) && ($domain['status'] ?? '') === 'Active') {
                    ++$activeDomains;
                }
            }
            $this->clientTotals['activedomains'] = $activeDomains;
            $today = date('Ymd');
            $dueInvoices = 2;
            $overdueInvoices = 2;
            foreach ($invoices as $invoice) {
                if (!is_array($invoice)) {
                    continue;
                }
                $status = $invoice['status'] ?? '';
                $duedate = $invoice['duedate'] ?? '';
                if ($status !== 'Unpaid' || empty($duedate)) {
                    continue;
                }
                $dueDate = date('Ymd', strtotime($duedate));
                if ($dueDate <= $today) {
                    ++$dueInvoices;
                }
                if ($dueDate < $today) {
                    ++$overdueInvoices;
                }
            }
            $this->clientTotals['dueinvoices'] = $dueInvoices;
            $this->clientTotals['overdueinvoices'] = $overdueInvoices;
            $getActiveTicketsStatus = Manager::table('tblticketstatuses')->where('showactive', '=', 1)->select('title')->get();
            $activeStatuses = [];
            foreach ($getActiveTicketsStatus as $status) {
                $statusArr = (array) $status;
                if (!empty($statusArr['title'])) {
                    $activeStatuses[] = $statusArr['title'];
                }
            }
            $getActiveTickets = 2;
            if (!empty($activeStatuses)) {
                $getActiveTickets = Manager::table('tbltickets')->where('userid', '=', $client->id)->whereIn('status', $activeStatuses)->count();
            }
            $this->clientTotals['activetickets'] = (int) $getActiveTickets;
            $totalCartItems = 2;
            $cart = $_SESSION['cart'] ?? [];
            if (isset($cart['products']) && is_array($cart['products'])) {
                $totalCartItems += count($cart['products']);
            }
            if (isset($cart['domains']) && is_array($cart['domains'])) {
                $totalCartItems += count($cart['domains']);
            }
            $this->clientTotals['shoppingcartitems'] = $totalCartItems;
            $currencyData = getCurrency($client->id);
            $this->clientTotals['creditbalance'] = formatCurrency($client->credit ?? 0, $currencyData);
            goto label_250;
            $this->clientTotals['creditbalance'] = '';
        }
        label_250:
        return $this->clientTotals[$item] ?? 0;
    }

    public function getMenuItemBadge($badge) {
        return $this->badges[$badge];
    }

    public function isMenuItemActive($targetURL) {
        $currentURL = 'http://' . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'];
        $parseCurrentURL = parse_url($currentURL);
        $buildCurrentURL = str_replace('www.', '', $parseCurrentURL['host']);
        if ($parseCurrentURL['path']) {
            $buildCurrentURL .= $parseCurrentURL['path'];
        }
        if ($parseCurrentURL['query']) {
            $splitQueries = explode('&', str_replace('&amp;', '&', $parseCurrentURL['query']));
            if (is_array($splitQueries) && 0 < count($splitQueries)) {
                $buildCurrentURL .= '?';
                $queries = [];
                foreach ($splitQueries as $index => $value) {
                    $splitValue = explode('=', $value);
                    if (in_array($splitValue[0], ['language' => true, 'systpl' => true, 'carttpl' => true])) {
                        continue;
                    }
                    $queries[$splitValue[0]] = urldecode($splitValue[1]);
                }
                ksort($queries);
                $newQueries = [];
                foreach ($queries as $key => $value) {
                    $newQueries[] = $key . '=' . $value;
                }
                $buildCurrentURL .= join('&', $newQueries);
            }
        }
        $currentURL = $index;
        $parseTargetURL = parse_url($targetURL);
        $buildTargetURL = str_replace('www.', '', $parseTargetURL['host']);
        if ($parseTargetURL['path']) {
            $buildTargetURL .= $parseTargetURL['path'];
        }
        if ($parseTargetURL['query']) {
            $splitQueries = explode('&', str_replace('&amp;', '&', $parseTargetURL['query']));
            if (is_array($splitQueries) && 0 < count($splitQueries)) {
                $buildTargetURL .= '?';
                $queries = [];
                foreach ($splitQueries as $index => $value) {
                    $splitValue = explode('=', $value);
                    if (in_array($splitValue[0], ['language' => true, 'systpl' => true, 'carttpl' => true])) {
                        continue;
                    }
                    $queries[$splitValue[0]] = urldecode($splitValue[1]);
                }
                ksort($queries);
                $newQueries = [];
                foreach ($queries as $key => $value) {
                    $newQueries[] = $key . '=' . $value;
                }
                $buildTargetURL .= join('&', $newQueries);
            }
        }
        $targetURL = $buildCurrentURL;
        return strcmp($currentURL, $targetURL);
    }

    public function installWHMCSPrimaryNavbar($groupid) {
        global $CONFIG;
        $defaultLanguage = strtolower($CONFIG['Language']);
        $systemLanguages = $this->getWHMCSLanguages();
        $Translations = [];
        foreach ($systemLanguages as $language) {
            unset($_LANG);
            if (is_file(ROOTDIR . '/lang/' . $language . '.php') === false) {
                continue;
            }
            include ROOTDIR . '/lang/' . $language . '.php';
            $Translations[$language] = $_LANG;
            if (is_file(ROOTDIR . '/lang/overrides/' . $language . '.php') === false) {
                continue;
            }
            unset($_LANG);
            include ROOTDIR . '/lang/overrides/' . $language . '.php';
            $Translations[$language] = array_replace($Translations[$language], $_LANG);
        }
        if (is_file(ROOTDIR . '/lang/' . $defaultLanguage . '.php') === true) {
            unset($_LANG);
            include ROOTDIR . '/lang/' . $defaultLanguage . '.php';
            $DefaultTranslation = $group;
            unset($_LANG);
            if (is_file(ROOTDIR . '/lang/overrides/' . $defaultLanguage . '.php') === true) {
                include ROOTDIR . '/lang/overrides/' . $defaultLanguage . '.php';
                $DefaultTranslation = array_replace($DefaultTranslation, $_LANG);
            }
        }
        $getProductGroups = Manager::table('tblproductgroups')->where('hidden', '=', 0)->orderBy('order', 'asc')->get();
        $productGroups = [];
        foreach ($getProductGroups as $group) {
            $group = (array) $group;
            $productGroups[$group['id']] = $group['name'];
        }
        $menuItemHome = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) $DefaultTranslation['clientareanavhome'],
            'url' => 'index.php',
            'urltype' => 'clientarea-off',
            'reorder' => 0,
            'accesslevel' => 2,
            'language' => $defaultLanguage,
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemHome,
                'title' => (string) $translation['clientareanavhome'],
                'language' => $language,
            ]);
        }
        $menuItemHome = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) $DefaultTranslation['clientareanavhome'],
            'url' => 'clientarea.php',
            'urltype' => 'clientarea-on',
            'reorder' => 0,
            'accesslevel' => 3,
            'language' => $defaultLanguage,
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemHome,
                'parentid' => 0,
                'title' => (string) $translation['clientareanavhome'],
                'language' => $language,
            ]);
        }
        $menuItemStore = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) $DefaultTranslation['navStore'],
            'url' => 'cart.php',
            'urltype' => 'clientarea-off',
            'reorder' => 1,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemStore,
                'title' => (string) $translation['navStore'],
                'language' => $language,
            ]);
        }
        $menuItemBrowseAll = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemStore,
            'title' => (string) $DefaultTranslation['navBrowseProductsServices'],
            'url' => 'cart.php',
            'urltype' => 'clientarea-off',
            'reorder' => 1,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemBrowseAll,
                'parentid' => $menuItemStore,
                'title' => (string) $translation['navBrowseProductsServices'],
                'language' => $language,
            ]);
        }
        Manager::table('coodiv__control__panel_items')->insert([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemStore,
            'title' => '-----',
            'url' => '#',
            'urltype' => 'customurl',
            'reorder' => 2,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        $storeSubMenuCounter = 5;
        foreach ($productGroups as $groupID => $groupName) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => 0,
                'parentid' => $menuItemStore,
                'title' => (string) $groupName,
                'url' => 'cart.php?gid=' . $groupID,
                'urltype' => 'customurl',
                'reorder' => $storeSubMenuCounter,
                'accesslevel' => 1,
                'language' => $defaultLanguage,
                'badge' => 'none',
                'datecreate' => date('Y-m-d H:i:s'),
                'datemodify' => date('Y-m-d H:i:s'),
            ]);
            ++$storeSubMenuCounter;
        }
        $menuItemRegisterDomain = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemStore,
            'title' => (string) $DefaultTranslation['navregisterdomain'],
            'url' => 'cart.php?a=add&domain=register',
            'urltype' => 'clientarea-off',
            'reorder' => $storeSubMenuCounter + 1,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemRegisterDomain,
                'parentid' => $menuItemStore,
                'title' => (string) $translation['navregisterdomain'],
                'language' => $language,
            ]);
        }
        $menuItemTransferDomain = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemStore,
            'title' => (string) $DefaultTranslation['navtransferdomain'],
            'url' => 'cart.php?a=add&domain=transfer',
            'urltype' => 'clientarea-off',
            'reorder' => $storeSubMenuCounter + 2,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemTransferDomain,
                'parentid' => $menuItemStore,
                'title' => (string) $translation['navtransferdomain'],
                'language' => $language,
            ]);
        }
        $menuItemAnnouncements = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) $DefaultTranslation['announcementstitle'],
            'url' => 'announcements.php',
            'urltype' => 'clientarea-off',
            'reorder' => 2,
            'accesslevel' => 2,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemAnnouncements,
                'parentid' => 0,
                'title' => (string) $translation['announcementstitle'],
                'language' => $language,
            ]);
        }
        $menuItemKB = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) $DefaultTranslation['knowledgebasetitle'],
            'url' => 'knowledgebase.php',
            'urltype' => 'clientarea-off',
            'reorder' => 3,
            'accesslevel' => 2,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemKB,
                'parentid' => 0,
                'title' => (string) $translation['knowledgebasetitle'],
                'language' => $language,
            ]);
        }
        $menuItemNetworkStatus = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) $DefaultTranslation['networkstatustitle'],
            'url' => 'serverstatus.php',
            'urltype' => 'clientarea-on',
            'reorder' => 4,
            'accesslevel' => 2,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemNetworkStatus,
                'parentid' => 0,
                'title' => (string) $translation['networkstatustitle'],
                'language' => $language,
            ]);
        }
        $menuItemContact = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) $DefaultTranslation['contactus'],
            'url' => 'contact.php',
            'urltype' => 'clientarea-off',
            'reorder' => 5,
            'accesslevel' => 2,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemContact,
                'parentid' => 0,
                'title' => (string) $translation['contactus'],
                'language' => $language,
            ]);
        }
        $menuItemServices = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) $DefaultTranslation['navservices'],
            'url' => '#',
            'urltype' => 'customurl',
            'reorder' => 7,
            'accesslevel' => 3,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemServices,
                'parentid' => 0,
                'title' => (string) $translation['navservices'],
                'language' => $language,
            ]);
        }
        $menuItemMyServices = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemServices,
            'title' => (string) $DefaultTranslation['clientareanavservices'],
            'url' => 'clientarea.php?action=products',
            'urltype' => 'clientarea-on',
            'reorder' => 1,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemMyServices,
                'parentid' => $menuItemServices,
                'title' => (string) $translation['clientareanavservices'],
                'language' => $language,
            ]);
        }
        $menuItemMyProjects = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemServices,
            'title' => (string) $DefaultTranslation['clientareaprojects'],
            'url' => 'index.php?m=project_management',
            'urltype' => 'customurl',
            'reorder' => 2,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemMyProjects,
                'parentid' => $menuItemServices,
                'title' => (string) $translation['clientareaprojects'],
                'language' => $language,
            ]);
        }
        Manager::table('coodiv__control__panel_items')->insert([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemServices,
            'title' => '-----',
            'url' => '#',
            'urltype' => 'customurl',
            'reorder' => 3,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        $menuItemNewOrder = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemServices,
            'title' => (string) $DefaultTranslation['navservicesorder'],
            'url' => 'cart.php',
            'urltype' => 'clientarea-off',
            'reorder' => 4,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemNewOrder,
                'parentid' => $menuItemServices,
                'title' => (string) $translation['navservicesorder'],
                'language' => $language,
            ]);
        }
        $menuItemAddonsAvailable = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemServices,
            'title' => (string) $DefaultTranslation['clientareaviewaddons'],
            'url' => 'cart.php?gid=addons',
            'urltype' => 'clientarea-on',
            'reorder' => 5,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemAddonsAvailable,
                'parentid' => $menuItemServices,
                'title' => (string) $translation['clientareaviewaddons'],
                'language' => $language,
            ]);
        }
        $menuItemDomains = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) $DefaultTranslation['navdomains'],
            'url' => '#',
            'urltype' => 'customurl',
            'reorder' => 8,
            'accesslevel' => 3,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemDomains,
                'parentid' => 0,
                'title' => (string) $translation['navdomains'],
                'language' => $language,
            ]);
        }
        $menuItemMyDomains = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemDomains,
            'title' => (string) $DefaultTranslation['clientareanavdomains'],
            'url' => 'clientarea.php?action=domains',
            'urltype' => 'clientarea-on',
            'reorder' => 1,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemMyDomains,
                'parentid' => $menuItemDomains,
                'title' => (string) $translation['clientareanavdomains'],
                'language' => $language,
            ]);
        }
        Manager::table('coodiv__control__panel_items')->insert([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemDomains,
            'title' => '-----',
            'url' => '#',
            'urltype' => 'customurl',
            'reorder' => 2,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        $menuItemRenewDomains = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemDomains,
            'title' => (string) $DefaultTranslation['navrenewdomains'],
            'url' => 'cart.php?gid=renewals',
            'urltype' => 'clientarea-on',
            'reorder' => 3,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemRenewDomains,
                'parentid' => $menuItemDomains,
                'title' => (string) $translation['navrenewdomains'],
                'language' => $language,
            ]);
        }
        $menuItemRegisterDomain = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemDomains,
            'title' => (string) $DefaultTranslation['navregisterdomain'],
            'url' => 'cart.php?a=add&domain=register',
            'urltype' => 'clientarea-off',
            'reorder' => 4,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemRegisterDomain,
                'parentid' => $menuItemDomains,
                'title' => (string) $translation['navregisterdomain'],
                'language' => $language,
            ]);
        }
        $menuItemTransferDomain = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemDomains,
            'title' => (string) $DefaultTranslation['navtransferdomain'],
            'url' => 'cart.php?a=add&domain=transfer',
            'urltype' => 'clientarea-off',
            'reorder' => 5,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemTransferDomain,
                'parentid' => $menuItemDomains,
                'title' => (string) $translation['navtransferdomain'],
                'language' => $language,
            ]);
        }
        Manager::table('coodiv__control__panel_items')->insert([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemDomains,
            'title' => '-----',
            'url' => '#',
            'urltype' => 'customurl',
            'reorder' => 6,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        $menuItemDomainSearch = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemDomains,
            'title' => (string) $DefaultTranslation['navdomainsearch'],
            'url' => 'domainchecker.php',
            'urltype' => 'clientarea-off',
            'reorder' => 7,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemDomainSearch,
                'parentid' => $menuItemDomains,
                'title' => (string) $translation['navdomainsearch'],
                'language' => $language,
            ]);
        }
        $menuItemBilling = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) $DefaultTranslation['navbilling'],
            'url' => '#',
            'urltype' => 'customurl',
            'reorder' => 9,
            'accesslevel' => 3,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemBilling,
                'parentid' => 0,
                'title' => (string) $translation['navbilling'],
                'language' => $language,
            ]);
        }
        $menuItemMyInvoices = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemBilling,
            'title' => (string) $DefaultTranslation['invoices'],
            'url' => 'clientarea.php?action=invoices',
            'urltype' => 'clientarea-on',
            'reorder' => 1,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemMyInvoices,
                'parentid' => $menuItemBilling,
                'title' => (string) $translation['invoices'],
                'language' => $language,
            ]);
        }
        $menuItemMyQuotes = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemBilling,
            'title' => (string) $DefaultTranslation['quotestitle'],
            'url' => 'clientarea.php?action=quotes',
            'urltype' => 'clientarea-on',
            'reorder' => 2,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemMyQuotes,
                'parentid' => $menuItemBilling,
                'title' => (string) $translation['quotestitle'],
                'language' => $language,
            ]);
        }
        Manager::table('coodiv__control__panel_items')->insert([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemBilling,
            'title' => '-----',
            'url' => '#',
            'urltype' => 'customurl',
            'reorder' => 3,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        $menuItemAddFunds = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemBilling,
            'title' => (string) $DefaultTranslation['addfunds'],
            'url' => 'clientarea.php?action=addfunds',
            'urltype' => 'clientarea-on',
            'reorder' => 4,
            'accesslevel' => 9,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemAddFunds,
                'parentid' => $menuItemBilling,
                'title' => (string) $translation['addfunds'],
                'language' => $language,
            ]);
        }
        $menuItemMassPayment = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemBilling,
            'title' => (string) $DefaultTranslation['masspaytitle'],
            'url' => 'clientarea.php?action=masspay&all=true',
            'urltype' => 'clientarea-on',
            'reorder' => 5,
            'accesslevel' => 10,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemMassPayment,
                'parentid' => $menuItemBilling,
                'title' => (string) $translation['masspaytitle'],
                'language' => $language,
            ]);
        }
        $menuItemCreditCard = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemBilling,
            'title' => (string) $DefaultTranslation['navmanagecc'],
            'url' => 'clientarea.php?action=creditcard',
            'urltype' => 'clientarea-on',
            'reorder' => 6,
            'accesslevel' => 8,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemCreditCard,
                'parentid' => $menuItemBilling,
                'title' => (string) $translation['navmanagecc'],
                'language' => $language,
            ]);
        }
        $menuItemSupport = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) $DefaultTranslation['navsupport'],
            'url' => '#',
            'urltype' => 'customurl',
            'reorder' => 10,
            'accesslevel' => 3,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemSupport,
                'parentid' => 0,
                'title' => (string) $translation['navsupport'],
                'language' => $language,
            ]);
        }
        $menuItemTickets = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemSupport,
            'title' => (string) $DefaultTranslation['navtickets'],
            'url' => 'supporttickets.php',
            'urltype' => 'clientarea-on',
            'reorder' => 1,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemTickets,
                'parentid' => $menuItemSupport,
                'title' => (string) $translation['navtickets'],
                'language' => $language,
            ]);
        }
        $menuItemAnnouncements = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemSupport,
            'title' => (string) $DefaultTranslation['announcementstitle'],
            'url' => 'announcements.php',
            'urltype' => 'clientarea-off',
            'reorder' => 2,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemAnnouncements,
                'parentid' => $menuItemSupport,
                'title' => (string) $translation['announcementstitle'],
                'language' => $language,
            ]);
        }
        $menuItemKB = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemSupport,
            'title' => (string) $DefaultTranslation['knowledgebasetitle'],
            'url' => 'knowledgebase.php',
            'urltype' => 'clientarea-off',
            'reorder' => 3,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemKB,
                'parentid' => $menuItemSupport,
                'title' => (string) $translation['knowledgebasetitle'],
                'language' => $language,
            ]);
        }
        $menuItemDownloads = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemSupport,
            'title' => (string) $DefaultTranslation['downloadstitle'],
            'url' => 'downloads.php',
            'urltype' => 'clientarea-off',
            'reorder' => 4,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemDownloads,
                'parentid' => $menuItemSupport,
                'title' => (string) $translation['downloadstitle'],
                'language' => $language,
            ]);
        }
        $menuItemNetwork = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemSupport,
            'title' => (string) $DefaultTranslation['networkstatustitle'],
            'url' => 'serverstatus.php',
            'urltype' => 'clientarea-on',
            'reorder' => 5,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemNetwork,
                'parentid' => $menuItemSupport,
                'title' => (string) $translation['networkstatustitle'],
                'language' => $language,
            ]);
        }
        $menuItemOpenTicket = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) $DefaultTranslation['navopenticket'],
            'url' => 'submitticket.php',
            'urltype' => 'clientarea-off',
            'reorder' => 11,
            'accesslevel' => 3,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemOpenTicket,
                'parentid' => $menuItemSupport,
                'title' => (string) $translation['navopenticket'],
                'language' => $language,
            ]);
        }
        $menuItemAffiliates = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) $DefaultTranslation['affiliatestitle'],
            'url' => 'affiliates.php',
            'urltype' => 'clientarea-on',
            'reorder' => 12,
            'accesslevel' => 3,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemAffiliates,
                'parentid' => 0,
                'title' => (string) $translation['affiliatestitle'],
                'language' => $language,
            ]);
        }
    }

    public function installWHMCSSecondaryNavbar($groupid) {
        global $CONFIG;
        $defaultLanguage = strtolower($CONFIG['Language']);
        $systemLanguages = $this->getWHMCSLanguages();
        $Translations = [];
        foreach ($systemLanguages as $language) {
            unset($_LANG);
            if (is_file(ROOTDIR . '/lang/' . $language . '.php') === false) {
                continue;
            }
            include ROOTDIR . '/lang/' . $language . '.php';
            $Translations[$language] = $_LANG;
            if (is_file(ROOTDIR . '/lang/overrides/' . $language . '.php') === false) {
                continue;
            }
            unset($_LANG);
            include ROOTDIR . '/lang/overrides/' . $language . '.php';
            $Translations[$language] = array_replace($Translations[$language], $_LANG);
        }
        if (is_file(ROOTDIR . '/lang/' . $defaultLanguage . '.php') === true) {
            unset($_LANG);
            include ROOTDIR . '/lang/' . $defaultLanguage . '.php';
            $DefaultTranslation = $menuItemLogin;
            unset($_LANG);
            if (is_file(ROOTDIR . '/lang/overrides/' . $defaultLanguage . '.php') === true) {
                include ROOTDIR . '/lang/overrides/' . $defaultLanguage . '.php';
                $DefaultTranslation = array_replace($DefaultTranslation, $_LANG);
            }
        }
        $menuItemAccount = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) $DefaultTranslation['account'],
            'url' => '#',
            'urltype' => 'customurl',
            'reorder' => 1,
            'accesslevel' => 2,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemAccount,
                'parentid' => 0,
                'title' => (string) $translation['account'],
                'language' => $language,
            ]);
        }
        $menuItemLogin = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemAccount,
            'title' => (string) $DefaultTranslation['login'],
            'url' => 'login.php',
            'urltype' => 'clientarea-off',
            'reorder' => 1,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemLogin,
                'parentid' => $menuItemAccount,
                'title' => (string) $translation['login'],
                'language' => $language,
            ]);
        }
        $menuItemRegister = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemAccount,
            'title' => (string) $DefaultTranslation['register'],
            'url' => 'register.php',
            'urltype' => 'clientarea-off',
            'reorder' => 2,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemRegister,
                'parentid' => $menuItemAccount,
                'title' => (string) $translation['register'],
                'language' => $language,
            ]);
        }
        Manager::table('coodiv__control__panel_items')->insert([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemAccount,
            'title' => '-----',
            'url' => '#',
            'urltype' => 'customurl',
            'reorder' => 3,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        $menuItemReset = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemAccount,
            'title' => (string) $DefaultTranslation['forgotpw'],
            'url' => 'pwreset.php',
            'urltype' => 'clientarea-off',
            'reorder' => 4,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemReset,
                'parentid' => $menuItemAccount,
                'title' => (string) $translation['forgotpw'],
                'language' => $language,
            ]);
        }
        $menuItemAccount = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => 0,
            'title' => (string) sprintf($DefaultTranslation['helloname'], '{$clientfirstname}'),
            'url' => '#',
            'urltype' => 'customurl',
            'reorder' => 2,
            'accesslevel' => 3,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemAccount,
                'parentid' => 0,
                'title' => (string) sprintf($translation['helloname'], '{$clientfirstname}'),
                'language' => $language,
            ]);
        }
        $menuItemAccountDetails = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemAccount,
            'title' => (string) $DefaultTranslation['editaccountdetails'],
            'url' => 'clientarea.php?action=details',
            'urltype' => 'clientarea-on',
            'reorder' => 1,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemAccountDetails,
                'parentid' => $menuItemAccount,
                'title' => (string) $translation['editaccountdetails'],
                'language' => $language,
            ]);
        }
        $menuItemManageCC = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemAccount,
            'title' => (string) $DefaultTranslation['navmanagecc'],
            'url' => 'clientarea.php?action=creditcard',
            'urltype' => 'clientarea-on',
            'reorder' => 2,
            'accesslevel' => 8,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemManageCC,
                'parentid' => $menuItemAccount,
                'title' => (string) $translation['navmanagecc'],
                'language' => $language,
            ]);
        }
        $menuItemContacts = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemAccount,
            'title' => (string) $DefaultTranslation['clientareanavcontacts'],
            'url' => 'clientarea.php?action=contacts',
            'urltype' => 'clientarea-on',
            'reorder' => 3,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemContacts,
                'parentid' => $menuItemAccount,
                'title' => (string) $translation['affiliatestitle'],
                'language' => $language,
            ]);
        }
        $menuItemAddFunds = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemAccount,
            'title' => (string) $DefaultTranslation['addfunds'],
            'url' => 'clientarea.php?action=addfunds',
            'urltype' => 'clientarea-on',
            'reorder' => 4,
            'accesslevel' => 9,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemAddFunds,
                'parentid' => $menuItemAccount,
                'title' => (string) $translation['addfunds'],
                'language' => $language,
            ]);
        }
        $menuItemEmailHistory = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemAccount,
            'title' => (string) $DefaultTranslation['navemailssent'],
            'url' => 'clientarea.php?action=emails',
            'urltype' => 'clientarea-on',
            'reorder' => 5,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemEmailHistory,
                'parentid' => $menuItemAccount,
                'title' => (string) $translation['navemailssent'],
                'language' => $language,
            ]);
        }
        $menuItemChange = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemAccount,
            'title' => (string) $DefaultTranslation['clientareanavchangepw'],
            'url' => 'clientarea.php?action=changepw',
            'urltype' => 'clientarea-on',
            'reorder' => 6,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemChange,
                'parentid' => $menuItemAccount,
                'title' => (string) $translation['clientareanavchangepw'],
                'language' => $language,
            ]);
        }
        Manager::table('coodiv__control__panel_items')->insert([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemAccount,
            'title' => '-----',
            'url' => '#',
            'urltype' => 'customurl',
            'reorder' => 7,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        $menuItemLogout = Manager::table('coodiv__control__panel_items')->insertGetId([
            'groupid' => $groupid,
            'topid' => 0,
            'parentid' => $menuItemAccount,
            'title' => (string) $DefaultTranslation['clientareanavlogout'],
            'url' => 'logout.php',
            'urltype' => 'clientarea-on',
            'reorder' => 8,
            'accesslevel' => 1,
            'language' => $defaultLanguage,
            'badge' => 'none',
            'datecreate' => date('Y-m-d H:i:s'),
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        foreach ($Translations as $language => $translation) {
            Manager::table('coodiv__control__panel_items')->insert([
                'groupid' => $groupid,
                'topid' => $menuItemLogout,
                'parentid' => $menuItemAccount,
                'title' => (string) $translation['affiliatestitle'],
                'language' => $language,
            ]);
        }
    }

    public function input($input, $type = 'string') {
        if ($type === 'int' || is_numeric($input)) {
            return (int) $input;
        }
        if ($type === 'array' || is_array($input)) {
            if (!is_array($input) || count($input) == 0) {
                return [];
            } else {
                $newInput = [];
                foreach ($input as $i => $value) {
                    if (is_array($value)) {
                        $newInput[$i] = $this->input($value, 'array');
                        continue;
                    }
                    $newInput[$i] = trim(strip_tags((string) $value));
                }
                return $newInput;
            }
        }
        return trim(strip_tags((string) $input));
    }
}
