import 'package:flutter/material.dart';
import 'models/custom_medication.dart';

class NotificationService {
  static Future<void> initialize() async {
    // Web version: notifications not supported
  }
  
  static Future<void> scheduleMedicationReminders(CustomMedication medication) async {
    // Web version: notifications not supported
  }
  
  static Future<void> cancelMedicationReminders(CustomMedication medication) async {
    // Web version: notifications not supported
  }
}