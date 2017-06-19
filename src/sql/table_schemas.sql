-- Track all property views and searches
CREATE TABLE public.history (
    user_id integer NOT NULL,
    action_type character varying(32) NOT NULL,
    action_text text NOT NULL,
    create_dt timestamp without time zone DEFAULT now() NULL
);
CREATE INDEX IX_history ON history (user_id, action_type);

-- Error tracking
CREATE TABLE public.error_log (
    user_id integer NOT NULL,
    error_id character varying(32) NOT NULL,
    error_desc character varying(512) NULL,
    error_url character varying(512) NOT NULL,
    debug_data bytea NULL,
    create_dt timestamp without time zone DEFAULT now() NULL
);
CREATE INDEX IX_error_log ON error_log (user_id);

-- Property groups
CREATE TABLE public.portfolios (
    portfolio_id SERIAL NOT NULL,
    user_id integer NOT NULL,
    portfolio_name character varying(128) NOT NULL,
    portfolio_type character varying(32) NOT NULL,
    create_dt timestamp without time zone DEFAULT now() NULL
);
CREATE INDEX IX_portfolios ON portfolios (user_id, portfolio_name);

-- Altered and saved property details
CREATE TABLE public.properties (
	property_id SERIAL NOT NULL,
    property_name character varying(64) NOT NULL,
    user_id integer NOT NULL,

    portfolio_id integer NOT NULL,
    is_owned boolean NOT NULL,
    street_address character varying(256) NOT NULL,
    zip_code character varying(16) NOT NULL,
    zpid integer NULL,
    latitude character varying(32) NULL,
    longitude character varying(32) NULL,

	-- Core
	valuation float NULL,
    purchase_price float NULL,
    rent float NULL,

    -- Mortgage
    down_payment_dollar float  NULL,
    down_payment_percent float  NULL,
    mortgage_rate float  NULL,
    mortgage_term integer  NULL,
    mortgage_points integer  NULL,

    -- Costs
    property_taxes float NULL,
    property_insurance float NULL,
    renovation_budget float NULL,
    hoa_misc float NULL,
    closing_costs_dollar float NULL,
    closing_costs_percent float  NULL,
    property_management_dollar float NULL,
    property_management_percent float  NULL,
    vacancy_rate_dollar float NULL,
    vacancy_rate_percent float  NULL,
    capex_dollar float NULL,
    capex_percent float  NULL,

    -- Soft
    images bytea NULL,
    finished_sqft character varying(8) NULL,
    bedrooms character varying(8) NULL,
    bathrooms character varying(8) NULL,

    update_dt timestamp without time zone DEFAULT now() NULL,
    create_dt timestamp without time zone DEFAULT now() NULL
);
CREATE INDEX IX_properties ON properties (property_name, user_id);
CREATE INDEX IX_properties_in_group ON properties (user_id, portfolio_id);

-- Get a user_id for everyone because Auth0 is annoying
CREATE TABLE public.user_details (
    user_id SERIAL NOT NULL,
    email character varying(512)  NOT NULL,
    access_level character varying(128) DEFAULT('basic') NOT NULL,
    stripe_id character varying(64) NULL,
    create_dt timestamp without time zone DEFAULT now() NULL,
    last_dt timestamp without time zone DEFAULT now() NULL
);
CREATE INDEX IX_user_details ON user_details (email, user_id);


/* COACHING SCHEMAS */
CREATE TABLE public.coaches (
    slug character varying(64)  NOT NULL,
    orderid integer NOT NULL,
    name character varying(128)  NULL,
    title character varying(128)  NULL,
    facebook character varying(256)  NULL,
    twitter character varying(256)  NULL,
    linkedin character varying(256)  NULL,
    short_bio text  NULL,
    long_bio text  NULL,
    long_bio_title text  NULL,
    is_active boolean DEFAULT(true)
);
CREATE UNIQUE INDEX ix_coaches_pkey ON coaches USING btree (slug);


CREATE TABLE public.coach_packages (
    package_id SERIAL NOT NULL,
    coach_slug character varying(64)  NOT NULL,
    package_slug character varying(64)  NOT NULL,
    orderid integer NOT NULL,
    title character varying(64)  NOT NULL,
    package_contents character varying(512)  NULL,
    price integer NOT NULL,
    monthly_sessions integer NOT NULL,
    is_active boolean DEFAULT(true)
);
CREATE INDEX IX_coach_packages ON coach_packages (coach_slug);


CREATE TABLE public.coach_package_sales (
    sale_id SERIAL NOT NULL,
    user_id integer NOT NULL,
    coach_slug character varying(64)  NOT NULL,
    package_id integer NOT NULL,
    price integer NOT NULL,
    is_scheduled boolean DEFAULT(false),
    is_paid_by_lmm boolean DEFAULT(false),
    purchase_dt timestamp without time zone DEFAULT now() NULL
);
CREATE INDEX IX_coach_package_sales ON coach_package_sales (sale_id);
CREATE INDEX IX_coach_package_sales_2 ON coach_package_sales (coach_slug, package_id);

CREATE TABLE public.change_log (
    change_id SERIAL NOT NULL,
    change_type character varying(64)  NOT NULL,
    change_description text,
    create_dt timestamp without time zone DEFAULT now() NULL
);
CREATE INDEX IX_change_log ON change_log (change_id);

CREATE TABLE fct_zillow(
   dt date,
   property_name character varying(64) NOT NULL,
   street_address character varying(64) NOT NULL,
   state character varying(2) NOT NULL,
   zip_code character varying(16) NOT NULL,
   zpid integer,
   latitude character varying(32),
   longitude character varying(32),
   valuation double precision,
   purchase_price double precision,
   rent double precision,
   images bytea,
   finished_sqft character varying(8),
   bedrooms character varying(8),
   bathrooms character varying(8)
);
CREATE INDEX IX_fct_zillow ON fct_zillow (property_name);


CREATE TABLE  fct_housecanary_details (
	dt date,
	property_name character varying(64) NOT NULL,

	no_of_buildings smallint,
	attic character varying(32),
	total_number_of_rooms smallint,
	heating character varying(64),
	heating_fuel_type character varying(64),

	property_type character varying(64),
	style character varying(64),
	garage_parking_of_cars smallint,

	site_area_acres double precision,
	number_of_units smallint,
	building_area_sq_ft smallint,
	total_bath_count double precision,
	garage_type_parking character varying(64),
	basement character varying(32),
	year_built smallint,
	air_conditioning character varying(32),
	building_quality_score character varying(32),
	fireplace character varying(32),
	pool character varying(32),
	no_of_stories character varying(32),
	water character varying(32),
	subdivision character varying(64),
	exterior_walls character varying(64),
	number_of_bedrooms smallint,
	sewer character varying(32),
	building_condition_score character varying(32),
	full_bath_count character varying(32),
	partial_bath_count character varying(32),
	assessment_year smallint,
	tax_amount double precision,
	total_assessed_value double precision,
	tax_year smallint
);
CREATE INDEX IX_fct_housecanary_details ON fct_housecanary_details (dt, property_name);

CREATE TABLE  fct_housecanary_census (
	property_name character varying(64) NOT NULL,
	msa_name character varying(64) NOT NULL,
	tribal_land character varying(8),
	block character varying(20),
	block_group character varying(20),
	tract character varying(20),
	county_name character varying(64) NOT NULL,
	fips character varying(8),
	msa character varying(8)
);
CREATE INDEX IX_fct_housecanary_census ON fct_housecanary_census (property_name);

CREATE TABLE fct_housecanary_sales_history (
	dt date,

	property_name character varying(64) NOT NULL,
	record_date date,
	record_doc character varying(64),

	fips character varying(8),
	event_type character varying(64),
	grantee_1 character varying(64),
	grantee_1_forenames character varying(64),
	grantee_2 character varying(64),
	grantee_2_forenames character varying(64),
	record_page smallint,
	amount double precision,
	grantor_1 character varying(64),
	grantor_1_forenames character varying(64),
	grantor_2 character varying(64),
	grantor_2_forenames character varying(64),
	apn character varying(64),
	record_book integer
);
CREATE INDEX IX_fct_housecanary_sales_history ON fct_housecanary_sales_history (dt, property_name, record_date, record_doc);

CREATE TABLE fct_housecanary_zip_details (
	dt date,
	property_name character varying(64) NOT NULL,
	mf_inventory_total double precision,
	mf_price_median double precision,
	mf_estimated_sales_total double precision,
	mf_market_action_median double precision,
	mf_months_of_inventory_median double precision,
	mf_days_on_market_median double precision,

	sf_inventory_total double precision,
	sf_price_median double precision,
	sf_estimated_sales_total double precision,
	sf_market_action_median double precision,
	sf_months_of_inventory_median double precision,
	sf_days_on_market_median double precision
);
CREATE INDEX IX_fct_housecanary_zip_details ON fct_housecanary_zip_details (dt, property_name);

-- Table: fct_housecanary_school - Mavu added 20170420
CREATE TABLE public.fct_housecanary_school (
  property_name character varying(64) DEFAULT NULL,
  elementary_city character varying(100),
  elementary_verified_school_boundaries character varying(32),
  elementary_distance_miles character varying(100),
  elementary_name character varying(100),
  elementary_zipcode character varying(100),
  elementary_phone character varying(20),
  elementary_state character varying(5),
  elementary_score character varying(100),
  elementary_education_level character varying(20),
  elementary_address character varying(255),
  elementary_assessment_year character varying(100),
  middle_city character varying(100),
  middle_verified_school_boundaries character varying(32),
  middle_distance_miles character varying(100),
  middle_name character varying(100),
  middle_zipcode character varying(100),
  middle_phone character varying(20),
  middle_state character varying(5),
  middle_score character varying(100),
  middle_education_level character varying(20),
  middle_address character varying(255),
  middle_assessment_year character varying(100),
  high_city character varying(100),
  high_verified_school_boundaries character varying(32),
  high_distance_miles character varying(100),
  high_name character varying(100),
  high_zipcode character varying(100),
  high_phone character varying(20),
  high_state character varying(5),
  high_score character varying(100),
  high_education_level character varying(20),
  high_address character varying(255),
  high_assessment_year character varying(100)
);
CREATE INDEX IX_fct_housecanary_school ON fct_housecanary_school (property_name);

-- Table: fct_housecanary_geocode - Mavu added 20170420
CREATE TABLE public.fct_housecanary_geocode (
  address_full character varying(255),
  slug character varying(255),
  address character varying(255),
  unit character varying(255),
  city character varying(255),
  state character varying(5),
  zipcode character varying(10),
  zipcode_plus4 character varying(10),
  block_id character varying(20),
  county_fips character varying(10),
  msa character varying(10),
  metdiv character varying(10),
  geo_precision character varying(20),
  lat character varying(32),
  lng character varying(32)
);

-- Master list of properties for sale/sold
CREATE TABLE dim_marketplace (
    marketplace_id SERIAL NOT NULL,
    property_name character varying(64) NOT NULL,
    property_uuid [something],

    is_active boolean DEFAULT(false),	-- list/delist property
    contract_by_user integer NULL,  -- user_id that is mid sales process
    is_sold boolean DEFAULT(false),

    -- Property Attributes
    purchase_price float NOT NULL,
    price_fixed boolean DEFAULT(true),
    cash_only boolean DEFAULT(false),

    -- Tenant Attributes
    has_tenant boolean DEFAULT(false),
    rent float NULL,

    -- Soft Details
    description text NULL,
    property_category integer NULL,		-- later use for marketplace categories

    listed_dt timestamp without time zone DEFAULT now() NULL,
 	contract_dt timestamp without time zone DEFAULT now() NULL,
 	sold_dt timestamp without time zone DEFAULT now() NULL
);
CREATE INDEX IX_dim_marketplace ON dim_marketplace (marketplace_id, property_name);

-- Drop dt column
ALTER TABLE public.fct_housecanary_geocode DROP COLUMN IF EXISTS dt;
ALTER TABLE public.fct_housecanary_school DROP COLUMN IF EXISTS dt;
ALTER TABLE public.fct_housecanary_census DROP COLUMN IF EXISTS dt;

-- Mavu - 20170504. is_trial = 0 not check trial otherwise compare trial_ends with now
ALTER TABLE public.user_details ADD COLUMN is_trial integer DEFAULT 0;

ALTER TABLE public.user_details
	ADD COLUMN "utm_source" character varying(32) DEFAULT NULL,
	ADD COLUMN "utm_medium" character varying(32) DEFAULT NULL,
	ADD COLUMN "utm_campaign" character varying(32) DEFAULT NULL;
