# **Aturan Pengaturan Parameter Config SCC Epever**

## 1. Urutan Perubahan Nilai

Setiap parameter **harus diatur secara berurutan dari nilai tertinggi ke nilai terendah** (atas ke bawah).

⚠️ **Tidak boleh ada nilai yang melanggar urutan hierarki** berikut:

```
overvoltage_disconnect  
> charging_limit_voltage  
> overvoltage_reconnect  
> equalize_charging_voltage  
> boost_charging_voltage  
> float_charging_voltage  
> boost_reconnect_charging_voltage  
> low_voltage_reconnect  
> undervoltage_warning_recover  
> undervoltage_warning  
> low_voltage_disconnect  
> discharging_limit_voltage
```

---

## 2. Parameter Penting

* **Reconnect Voltage:**
  `low_voltage_reconnect` → tegangan saat sistem kembali aktif setelah low voltage.

* **Cutoff Voltage:**
  `low_voltage_disconnect` → tegangan saat sistem memutuskan beban untuk melindungi baterai.

Parameter lain (`undervoltage_warning_recover`, `undervoltage_warning`, `discharging_limit_voltage`) harus tetap mengikuti urutan di atas.

---

## 3. Contoh Konfigurasi yang Benar

```json
{
  "overvoltage_disconnect": 5800,
  "charging_limit_voltage": 5770,
  "overvoltage_reconnect": 5750,
  "equalize_charging_voltage": 5730,
  "boost_charging_voltage": 5700,
  "float_charging_voltage": 5670,
  "boost_reconnect_charging_voltage": 5650,
  "low_voltage_reconnect": 4700,
  "undervoltage_warning_recover": 4650,
  "undervoltage_warning": 4630,
  "low_voltage_disconnect": 4600,
  "discharging_limit_voltage": 4550
}
```
---
