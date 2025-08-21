# **Aturan Pengaturan Parameter Config SCC SRNE**

## 1. Urutan Perubahan Nilai

Setiap parameter **harus diatur secara berurutan dari nilai tertinggi ke nilai terendah** (atas ke bawah).

⚠️ **Tidak boleh ada nilai yang melanggar urutan hierarki** berikut:

```
overvoltage_threshold
> charging_limit_voltage
> equalizing_charge_voltage
> boost_charging_voltage
> floating_charging_voltage
> boost_charging_recovery_voltage
> overdischarge_recovery_voltage
> undervoltage_warning_level
> overdischarge_voltage
> discharging_limit_voltage
```

---

## 2. Parameter Penting

* **Reconnect Voltage**
  `overdischarge_recovery_voltage` → tegangan saat sistem kembali aktif setelah **low voltage**.

* **Cutoff Voltage**
  `discharging_limit_voltage` → tegangan saat sistem memutuskan beban untuk melindungi baterai.

Parameter lain (`undervoltage_warning_level`, `overdischarge_voltage`) harus tetap mengikuti urutan di atas.

---

## 3. Contoh Konfigurasi yang Benar

```json
{
  "overvoltage_threshold": 160,
  "charging_limit_voltage": 147,
  "equalizing_charge_voltage": 147,
  "boost_charging_voltage": 146,
  "floating_charging_voltage": 145,
  "boost_charging_recovery_voltage": 143,
  "overdischarge_recovery_voltage": 118,
  "undervoltage_warning_level": 117,
  "overdischarge_voltage": 115,
  "discharging_limit_voltage": 113
}
```

---

## 4. Catatan Perhitungan Nilai

Setiap parameter ditulis dalam satuan skala **×40**.
Artinya, untuk mengetahui nilai asli (format 4 digit, misalnya `5300`), lakukan perhitungan:

* `overdischarge_recovery_voltage: 118`
  → **118 × 40 = 4720 mV** → reconnect di **4.72 V**

* `discharging_limit_voltage: 113`
  → **113 × 40 = 4520 mV** → cutoff di **4.52 V**

---
