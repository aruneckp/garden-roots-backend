-- Migration 18: Add collection_hours column to pickup_locations

ALTER TABLE pickup_locations ADD collection_hours VARCHAR2(100);

