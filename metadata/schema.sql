/*
 Navicat Premium Data Transfer

 Source Server         : PostgreSQL @ tesla
 Source Server Type    : PostgreSQL
 Source Server Version : 90004
 Source Host           : localhost
 Source Database       : googleoffers
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 90004
 File Encoding         : utf-8

 Date: 01/23/2012 14:48:54 PM
*/

-- ----------------------------
--  Table structure for "categories"
-- ----------------------------
DROP TABLE IF EXISTS "categories" CASCADE;
CREATE TABLE "categories" (
	"category_id" varchar(100) PRIMARY KEY,
    name varchar(100),
    label varchar(100)
)
WITH (OIDS=FALSE);
ALTER TABLE "categories" OWNER TO "postgres";

-- ----------------------------
--  Table structure for "promotions"
-- ----------------------------
DROP TABLE IF EXISTS "promotions" CASCADE;
CREATE TABLE "promotions" (
	"promotion_id" varchar(100) PRIMARY KEY,
    --first_observed, 
    marketplace_status varchar(50), 
    name varchar(100),
    start_date timestamp,
    end_date timestamp,
    category_id varchar(100) REFERENCES categories (category_id)
)
WITH (OIDS=FALSE);
ALTER TABLE "promotions" OWNER TO "postgres";

-- ----------------------------
--  Table structure for "markets"
-- ----------------------------
DROP TABLE IF EXISTS "markets" CASCADE;
CREATE TABLE "markets" (
	"market_id" varchar(100) PRIMARY KEY,
    name varchar(100)
)
WITH (OIDS=FALSE);
ALTER TABLE "markets" OWNER TO "postgres";

-- ----------------------------
--  Table structure for "promotion_market"
-- ----------------------------
DROP TABLE IF EXISTS "promotion_market";
CREATE TABLE "promotion_market" (
	"promotion_id" varchar(100) REFERENCES promotions (promotion_id),
	"market_id" varchar(100) REFERENCES markets (market_id)
)
WITH (OIDS=FALSE);
ALTER TABLE "promotion_market" OWNER TO "postgres";

-- ----------------------------
--  Table structure for "promotion_status_history"
-- ----------------------------
DROP TABLE IF EXISTS "promotion_status_history";
CREATE TABLE "promotion_status_history" (
	"promotion_id" varchar(100) REFERENCES promotions (promotion_id),
	"status" varchar(100),
	"last_update" timestamp(6) NULL
)
WITH (OIDS=FALSE);
ALTER TABLE "promotion_status_history" OWNER TO "postgres";

-- ----------------------------
--  Table structure for "redemption_codes"
-- ----------------------------
DROP TABLE IF EXISTS "redemption_codes";
CREATE TABLE "redemption_codes" (
	"promotion_id" varchar(100) REFERENCES promotions (promotion_id),
	"size" int4,
	"status" varchar(20),
	"last_update" timestamp(6) NULL
)
WITH (OIDS=FALSE);
ALTER TABLE "redemption_codes" OWNER TO "postgres";
